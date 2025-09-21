# The Examples of Contract Bugs

**ID** | **Vulnerability Name** | **Severity** | **ID** | **Vulnerability Name** | **Severity**
--- | --- | --- | --- | --- | ---
RE     | reentrancy-eth          | High     | UCL    | unchecked-lowlevel      | Medium   
SU     | suicidal                | High     | UCS    | unchecked-send          | Medium      
CDC    | controlled-delegatecall | High     | TO     | tx-origin               | Medium      
AS     | arbitrary-send          | High     | TS    | timestamp              | Low      
UIS    | uninitialized-state     | High | BP    | block-other-parameters | Low
UIO    | uninitialized-storage    | High | LLC   | low-level-calls        | Info
TOD    | TOD-ether/receiver      | High     | MEZ   | msgvalue-equals-zero        | Info     
IE     | incorrect-equality      | Medium   | ST    | send-transfer          | Opt    
IO     | integer-overflow        | Medium   | BE    | boolean-equal          | Opt     

We combine the contract code to explain the vulnerability examples supported by RSymX in terms of occurrence principle, severity, repair countermeasures, and insights at bytecode level.

## Bug_description.xlsx

This document describes the description of vulnerabilities. Some vulnerabilities are introduced as follows.

---

### Reentrancy

Reentrant function calls can cause smart contracts to behave in unexpected ways. Below are several types of reentrancy vulnerabilities and corresponding mitigation strategies:

---

#### (1) **Reentrancy with Ether (`reentrancy-eth`, RE):**
This vulnerability involves reentrant calls that transfer Ether. A typical example is using `call.value` for fund withdrawal, which may allow an attacker to recursively invoke the withdrawal function and drain funds before the contract updates the user's balance.

```solidity
contract ReentrancyEth {
	mapping(address=>uint256) public userBalance;
	function deploy() public payable {
		userBalance[msg.sender] += msg.value;
	}
	function withdrawBalance(){
		// send userBalance[msg.sender] Ether to msg.sender
		// if msg.sender is a contract, it will call its fallback function
		if( ! (msg.sender.call.value(userBalance[msg.sender])() ) ){
			throw;
		}
		userBalance[msg.sender] = 0;
	}
	function() public {}
}
```

As shown in Code Listing \ref{listing\:chap6\_reentrancy-eth}, the vulnerable contract `ReentrancyEth` performs a fund transfer using `call.value` in its `withdrawBalance()` function, but only updates the balance afterward. An attacker can deploy an auxiliary attack contract with a `fallback` function that calls `withdrawBalance()` again during the callback phase. By calling `exploitcall()` to deposit and then withdraw, the attacker repeatedly triggers the vulnerable function through reentrancy before the balance is updated, ultimately stealing the entire balance of the `ReentrancyEth` contract until the available gas is exhausted.

```solidity
contract ReentranceExploit {
	address owner; //Attack settings
	ReentrancyEth reentrancy;
	function ReentranceExploit() payable{
		owner = msg.sender;
	}
	function exploitcall(ReentrancyEth reentrancyeth) payable{
		reentrancy = reentrancyeth;
		reentrancyeth.deploy{value: msg.value}());
		reentrancyeth.withdrawBalance();
	}
	function get_money(){
		suicide(owner); //Destroy contract and get assets.
	}
	function() payable{
		reentrancy.withdrawBalance();
	}
}
```

**Remediation:**
Apply the **checks-effects-interactions pattern** by updating internal state before making external calls, and use the `transfer` function for Ether transfers to leverage its built-in gas limit and exception handling. The fixed contract is shown in Code Listing \ref{listing\:chap6\_reentrancy-eth-fixed}.

```solidity
contract ReentrancyEth {
	mapping(address=>uint256) public userBalance;
	function deploy() public payable {
		userBalance[msg.sender] += msg.value;
	}
	function withdrawBalance(){
		// send userBalance[msg.sender] Ether to msg.sender
		// if msg.sender is a contract, it will call its fallback function
		transfervalue = userBalance[msg.sender];
		userBalance[msg.sender] = 0;
		msg.sender.transfer(transfervalue);
	}
	function() public {}
}
```

---

#### (2) ** Reentrancy without Ether (`reentrancy-no-eth`, REN):**
Similar to `reentrancy-eth`, this vulnerability involves reentrant calls with **zero Ether transferred**, and while less harmful, it is still a violation of secure coding practices.

```solidity
bool not_called = true;
function bug(){
	require(not_called);
	if( ! (msg.sender.call.value(0)() ) ){
		throw;
	}
	not_called = false;
}
```

Code Listing \ref{listing\:chap6\_reentrancy-no-eth} shows a simplified vulnerable function `bug()` where `call.value(0)` is used, and a variable `not_called` is intended as a reentrancy lock. However, since the lock is set **after** the external call, it fails to prevent reentrancy. An attacker can use an auxiliary contract to repeatedly invoke `bug()` through the fallback function.

**Remediation:**
Use the same approach as above, i.e., **apply the checks-effects-interactions pattern** and replace `call.value` with `transfer`. The fixed version is shown in Code Listing \ref{listing\:chap6\_reentrancy-no-eth-fixed}.

```solidity
bool not_called = true;
function bug(){
	require(not_called);
	not_called = false;
	msg.sender.transfer(0);	
}
```

---

#### (3) ** Reentrancy via Events (`reentrancy-events`, REE):**
This vulnerability refers to reentrant calls that disrupt the **ordering of emitted events**, potentially misleading third-party services that rely on those logs.

```solidity
function bug(Called d){
	counter += 1;
	d.f();
	emit Counter(counter);
}
```

As demonstrated in Code Listing \ref{listing\:chap6\_reentrancy-events}, reentrancy in function `bug()` causes function `d.f()` to be repeatedly executed, but without proper event sequencing. This results in the `Counter` event being logged out of order, which could mislead downstream applications or services that depend on accurate event logs.

**Remediation:**
Apply the **checks-effects-interactions pattern** for all external calls to ensure events are emitted in a well-defined order. The fixed version is shown in Code Listing \ref{listing\:chap6\_reentrancy-events-fixed}.

```solidity
function bug(Called d){
	counter += 1;
	emit Counter(counter);
	d.f();
}
```

---

### **Arithmetic**

Arithmetic errors caused by overflow in numerical operations can lead to incorrect computation results, potentially causing the system or program to behave inconsistently with its intended logic. This may affect the stability and accuracy of the contract's execution.

---

#### (1) **Integer Overflow (`integer-overflow`, IO):**

Integer overflow occurs when a mathematical operation exceeds the maximum value or lower than the minimum representable by a given type. For example, if a number is stored as `uint8`, it is stored as an 8-bit unsigned integer, with a value range of 0 to \$2^8 - 1\$. Adding 1 to the maximum value (\$2^8 - 1\$) results in an integer overflow.

```solidity
contract Integeroverflow{
	function bad(uint256 a, uint256 b, uint256 c) public returns (uint256) {
		uint256 d = a + b;
		uint256 e = d - c;
		return e;
	}
}
```

As shown in Listing \ref{listing\:chap6\_integer-overflow}, when a user calls the `bad()` function with inputs (1, $ 2^{256}-1 $, 0), the function returns 0. This is because the `uint256` type has a range of \[0, $ 2^{256}-1 $], and any value exceeding $ 2^{256}-1 $ wraps around due to modular arithmetic, resulting in an overflow. Also, an underflow will be triggered if the inputs are (0, 0, 1), and the function returns $ 2^{256}-1 $.

**Remediation:**
For operations like addition, it is important to verify whether the result will cause an overflow. This can be done using `require` statements to check whether the result `d` is greater than either `a` or `b`. Also, the the result `e` should lower than `d`. Additionally, if the contract involves many arithmetic operations, it is advisable to use the `SafeMath` library to perform these computations securely. A corrected version of the contract using overflow checks is shown in Listing \ref{listing\:chap6\_integer-overflow-fixed}.

```solidity
contract Integeroverflow{
	function bad(uint256 a, uint256 b, uint256 c) public returns (uint256) {
		uint256 d = a + b;
		require(d >= a);
		uint256 e = d - c;
		require(e <= d);
		return e;
	}
}
```

---

### **Unchecked Calls**

Failing to check the results or parameters of internal/external function calls within a contract can lead to unexpected logical errors or exceptions.

#### (1) **Unchecked Low-Level Call (`unchecked-lowlevel`, UCL)**

This vulnerability refers to situations where a low-level external contract call fails, but the return value is not checked, potentially causing unintended consequences. For example, if `call.value()` is used to transfer funds and its return value is not checked, the balance of the sender may be deducted even if the transfer fails. In such a case, the user does not receive the funds, but their balance has already been reduced.

```solidity
mapping(address=>uint256) public userBalance;
function lowlevel_withdraw(address dst, uint value) public payable{
	if(value <= userBalance[dst]){
		userBalance[dst] -= value;
		dst.call.value(value)("");
	}
}
```

As shown in Listing \ref{listing\:chap6\_unchecked-lowlevel}, the `lowlevel_withdraw()` function fails to verify the return result of the `call.value` withdrawal operation. If the withdrawal fails due to the recipient account being temporarily unable to accept funds, yet its asset balance in the contract still decreases.

**Remediation:**
When using low-level calls, it is essential to validate the return value. If the call fails, appropriate fallback or revert operations should be executed. The corrected contract implementing this check is shown in Listing \ref{listing\:chap6\_unchecked-lowlevel-fixed}.

```solidity
mapping(address=>uint256) public userBalance;
function lowlevel_withdraw(address dst, uint value) public payable{
	if(value <= userBalance[dst]){
		userBalance[dst] -= value;
		if(!dst.call.value(value)("")){
			userBalance[dst] += value;
		}
	}
}
```

---

#### (2) **Unchecked Send (`unchecked-send`, UCS)**

Similar to `unchecked-lowlevel`, this vulnerability involves failure to check the return value of a `send` operation or other high-level calls.

```solidity
mapping(address=>uint256) public userBalance;
function send_withdraw(address dst, uint value) public payable{
	if(value <= userBalance[dst]){
		userBalance[dst] -= value;
		dst.send(value);
	}
}
```

As shown in Listing \ref{listing\:chap6\_unchecked-send}, just like the `unchecked-lowlevel` issue, the `send_withdraw()` function does not verify the return result of the `send` withdrawal operation. This may result in users not receiving the transferred amount while their balance within the contract is still reduced.

**Remediation:**
When using the `send` operation, the return value must be checked. In case of failure, fallback or rollback mechanisms should be triggered. The corrected contract with proper return value validation is shown in Listing \ref{listing\:chap6\_unchecked-send-fixed}.

```solidity
mapping(address=>uint256) public userBalance;
function send_withdraw(address dst, uint value) public payable{
	if(value <= userBalance[dst]){
		userBalance[dst] -= value;
		if(!dst.send(value)){
			userBalance[dst] += value;
		}
	}
}
```

### **Optimized Operations**

Certain operations in smart contracts can be optimized to enhance execution efficiency and reduce computational costs, such as gas usage at runtime. These optimizations also improve code readability, making future maintenance easier. Optimization techniques include, but are not limited to, algorithm improvements, code simplification, and elimination of unnecessary steps.

#### (1) **Send vs. Transfer (`send-transfer`, ST)**

When performing ETH transfers, it is recommended to use `addr.transfer(x)` instead of `send`. Although both `transfer` and `send` impose a 2300 gas stipend, `transfer` is safer as it automatically throws an exception and reverts the transaction upon failure, whereas `send` does not.

```solidity
function send_func(address addr, uint value) public payable{
	if(!addr.send(value)) {
		revert();
	}
}
```

As shown in Listing \ref{listing\:chap6\_send-transfer}, the function `send_func()` uses `send` for withdrawals and triggers a `revert()` on failure. This behavior is functionally equivalent to using `transfer` directly.

**Remediation:**
Replace `send` with `transfer` for withdrawals. The optimized contract is shown in Listing \ref{listing\:chap6\_send-transfer-fixed}.

```solidity
function send_func(address addr, uint value) public payable{
	if(!addr.send(value)) {
		revert();
	}
}
```

---

#### (2) **Code With No Effects (`code-no-effects`, CNE)**

In Solidity, it is possible to write code that does not produce any effect, and the compiler will not issue a warning. This can lead to “dead” code that fails to execute the intended operation. For example, omitting the final parentheses in `call.value()("")` can result in the function continuing execution without transferring funds.

```solidity
pragma solidity ^0.5.0;
contract Wallet {
	mapping(address => uint) balance;
	// Withdraw funds from contract
	function withdraw(uint amount) public {
		require(amount <= balance[msg.sender], 'amount must be less than balance');
		uint previousBalance = balance[msg.sender];
		balance[msg.sender] = previousBalance - amount;
		// Attempt to send amount from the contract to msg.sender
		msg.sender.call.value(amount);
	}
}
```

As shown in Listing \ref{listing\:chap6\_send-transfer}, the `withdraw()` function in the `Wallet` contract uses an incorrect `call.value` expression. Although this line does not raise a compilation error, it fails to execute, causing the user’s balance to decrease while no funds are actually transferred.

**Remediation:**
Fix the invalid call by appending the required parentheses to `call.value(amount)("")`. The corrected contract is shown in Listing \ref{listing\:chap6\_code-no-effects-fixed}.

```solidity
pragma solidity ^0.5.0;
contract Wallet {
	mapping(address => uint) balance;
	// Withdraw funds from contract
	function withdraw(uint amount) public {
		require(amount <= balance[msg.sender], 'amount must be less than balance');
		uint previousBalance = balance[msg.sender];
		balance[msg.sender] = previousBalance - amount;
		// Attempt to send amount from the contract to msg.sender
		msg.sender.call.value(amount)("");
	}
}
```

---

#### (3) **Revert vs. Require (`revert-require`, RR)**

The statement `if (condition) { revert(); }` can be replaced with `require(!condition)` to improve code readability and reduce gas costs.

```solidity
contract Holder {
	uint public holdUntil;
	address public holder;
	function withdraw () external {
		if (now < holdUntil){
			revert();
		}
		holder.transfer(this.balance);
	}
}
```

As shown in Listing \ref{listing\:chap6\_revert-require}, the `withdraw()` function in the `Holder` contract uses `if () revert()` logic, which is functionally equivalent to a `require()` statement. The latter is more concise and readable.

**Remediation:**
Replace `if...revert()` constructs with `require()` statements. The optimized version of the contract is shown in Listing \ref{listing\:chap6\_revert-require-fixed}.

```solidity
contract Holder {
	uint public holdUntil;
	address public holder;
	function withdraw () external {
		require(!(now < holdUntil));
		holder.transfer(this.balance);
	}
}
```

---

#### (4) **Unused State Variables (`unused-state`, UUS)**

Solidity allows the declaration of state variables that are never used. While they do not pose a direct security risk, they increase contract size and deployment gas costs, and they clutter the code.

```solidity
contract Unusedstates{
	address unused;
	address public unused2;
	address private unused3;
	address unused4;
	address used;
	function ceshi1 () external{
		unused3 = address(0);
	}
}
```

As shown in Listing \ref{listing\:chap6\_unused-state}, the `Unusedstates` contract declares several unused state variables (`unused`, `unused2`, `unused4`, `used`) that are never referenced, resulting in unnecessary gas consumption during deployment.

**Remediation:**
Remove unused state variables such as `unused`, `unused2`, `unused4`, and `used`. The optimized contract is shown in Listing \ref{listing\:chap6\_unused-state-fixed}.

```solidity
contract Unusedstates{
	address private unused3;
	function ceshi1 () external{
		unused3 = address(0);
	}
}
```

---

#### (5) **Extra Gas in Loops (`extra-gas-inloops`, EGL)**

The use of non-memory state variables such as `.balance` or `.length` in `for` or `while` loop conditions can introduce unnecessary gas overhead. This is because these state variables are re-evaluated on every iteration, even if their values do not change during the loop execution.

```solidity
contract NewContract {
	uint[] ss;
	function longLoop() {
		for(uint i = 0; i < ss.length; i++) {
			uint a = ss[i];
			/* ... */
		}
	}
}
```

As shown in Listing \ref{listing\:chap6\_extra-gas-inloops}, the `longLoop()` function in the `NewContract` contract compares against `ss.length` in every iteration of the `for` loop. Since the state variable `ss` is not modified during the loop, its `.length` remains constant. Repeatedly reading the same value from storage incurs avoidable gas consumption.

**Remediation:**
Store the `.length` value in a local variable before the loop and use that in the loop condition to reduce gas usage. The optimized contract is shown in Listing \ref{listing\:chap6\_extra-gas-inloops-fixed}.

```solidity
contract NewContract {
	uint[] ss;
	function longLoop() {
		uint listlen = ss.length;
		for(uint i = 0; i < listlen; i++) {
			uint a = ss[i];
			/* ... */
		}
	}
}
```

---

#### (6) **Costly Operations in Loops (`costly-operations-loop`, COL)**

Operations on state variables (e.g., `SSTORE`, `SLOAD`) are significantly more expensive in terms of gas than operations on local or memory variables (`MSTORE`, `MLOAD`). Repeated state variable access or modification inside loops can cause excessive gas consumption and may even lead to out-of-gas errors.

```solidity
contract CostlyOperationsInLoop {
	uint[] ss;
	uint state_variable = 0;
	function bad_loop(uing loop_count) external {
		uint listlen = ss.length；
		for (uint i = 0; i < listlen; i++) {
			state_variable+=ss[i];
		}
	}
}
contract CostlyOperationsInLoop {
	uint state_variable = 0;
	function bad_loop(uing loop_count) external {
		for (uint i = 0; i < loop_count; i++) {
			state_variable++;
		}
	}
}
```

As illustrated in Listing \ref{listing\:chap6\_costly-operations-loop}, the `bad_loop()` function in the `CostlyOperationsInLoop` contract performs repeated increment operations directly on a state variable inside the loop. This is inefficient.

**Remediation:**
Use a local variable to accumulate values inside the loop and assign the result to the state variable after the loop completes. The optimized contract is shown in Listing \ref{listing\:chap6\_costly-operations-loop-fixed}.

```solidity
contract CostlyOperationsInLoop {
	uint state_variable = 0;
	function bad_loop(uint loop_count) external {
		uint local_state_variable = state_variable;
		for (uint i = 0; i < loop_count; i++) {
			local_state_variable++;
		}
		state_variable = local_state_variable;
	}
}
```

---

#### (7) **Redundant Statements (`redundant-statements`, RDS)**

This issue is similar to the **code-no-effects** optimization but focuses on unnecessary code that has no operational effect and only wastes gas and harms code readability. While `code-no-effects` can introduce incorrect or unintended behavior, **redundant statements** are simply wasteful and clutter the codebase.

```solidity
contract RedundantStatementsContract {
	constructor() public {
		uint; // Elementary Type Name
		bool; // Elementary Type Name
		RedundantStatementsContract; // Identifier
	}
	
	function test() public returns (uint) {
		uint; // Elementary Type Name
		assert; // Identifier
		test; // Identifier
		return 777;
	}
}
```

As shown in Listing \ref{listing\:chap6\_redundant-statements}, declarations like `uint`, `bool`, and contract/identifier declarations such as `RedundantStatementsContract` that do not perform any operations will not generate any bytecode. These lines do not contribute to functionality and may confuse readers.

**Remediation:**
Delete redundant lines such as unused type declarations and other no-op identifiers. The optimized contract is shown in Listing \ref{listing\:chap6\_redundant-statements-fixed}.

```solidity
contract RedundantStatementsContract {
	constructor() public {
		uint; // Elementary Type Name
		bool; // Elementary Type Name
		RedundantStatementsContract; // Identifier
	}
	
	function test() public returns (uint) {
		uint; // Elementary Type Name
		assert; // Identifier
		test; // Identifier
		return 777;
	}
}
```

---

#### (8) **Boolean Equality (`boolean-equal`, BE)**

Comparing boolean variables explicitly with `true` or `false` is redundant and results in unnecessary gas consumption due to additional `EQ` operations.

```solidity
contract BooleanEqual {
	function badboolean(bool x) public {
		// ...
		if (x == true) { // bad!
			// ...
		}
		if (x == false) { // bad!
			// ...
		}
		// ...
	}
}
```

As shown in Listing \ref{listing\:chap6\_boolean-equal}, the `badboolean()` function in the `BooleanEqual` contract compares a boolean variable `x` with `true` or `false`. Since `x` is already a boolean, it can be used directly in conditional statements.

**Remediation:**
Eliminate unnecessary boolean comparisons. Replace expressions like `if (x == true)` with `if (x)` and `if (x == false)` with `if (!x)`. The optimized contract is shown in Listing \ref{listing\:chap6\_boolean-equal-fixed}.

```solidity
contract BooleanEqual {
	function badboolean(bool x) public {
		// ...
		if (x == true) { // bad!
			// ...
		}
		if (x == false) { // bad!
			// ...
		}
		// ...
	}
}
```

---

#### (9) **Array Instead of Bytes (`array-instead-bytes`, AIB)**

In Solidity, `byte[]` can typically be replaced with the `bytes` type to save gas. Both types serve the same purpose, but `bytes` is more efficient in terms of gas usage.

```solidity
contract C {
	byte[] someVariable;
	// ...
}
```

As shown in Listing \ref{listing\:chap6\_array-instead-bytes}, the state variable `someVariable` in contract `C` is declared as `byte[]`, but it can be replaced by `bytes` without affecting functionality and with better gas efficiency.

**Remediation:**
Replace all `byte[]` declarations with `bytes`. The optimized contract is shown in Listing \ref{listing\:chap6\_array-instead-bytes-fixed}.

```solidity
contract C {
	byte[] someVariable;
	// ...
}
```

---

#### (10) **Constable States (`constable-states`, CS)**

State variables initialized with constant values and never modified thereafter can be declared as `constant` to reduce gas consumption when accessed.

```solidity
contract B {
	address public mySistersAddress = 0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E;
	address public myFriendsAddress;
	address constant MY_ADDRESS = 0x999999cf1046e68e36E1aA2E0E07105eDDD1f08D;
	
	uint public used;
	
	function setUsed(uint a) public {
		if (msg.sender == MY_ADDRESS) {
			used = a;
			myFriendsAddress = 0xc0ffee254729296a45a3885639AC7E10F9d54980;
		}
	}
}
```

As shown in Listing \ref{listing\:chap6\_constable-states}, the variable `mySistersAddress` in contract `B` is assigned a fixed address and is never modified. Therefore, it can be declared as a `constant`, similar to `MY_ADDRESS`, to save gas during access.

**Remediation:**
Add the `constant` keyword to any state variable that holds an immutable value. The optimized version is shown in Listing \ref{listing\:chap6\_constable-states-fixed}.

```solidity
contract B {
	address public constant mySistersAddress = 0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E;
	address public myFriendsAddress;
	address constant MY_ADDRESS = 0x999999cf1046e68e36E1aA2E0E07105eDDD1f08D;
	
	uint public used;
	
	function setUsed(uint a) public {
		if (msg.sender == MY_ADDRESS) {
			used = a;
			myFriendsAddress = 0xc0ffee254729296a45a3885639AC7E10F9d54980;
		}
	}
}
```

---

#### (11) **Return Struct (`return-struct`, RTS)**

For internal or private functions with multiple return values, it is recommended to encapsulate the return values in a `struct`. This improves code readability and maintainability—especially when the return values may change over time.

```solidity
contract TestContract {
	function test() internal returns(uint a, address b, bool c, int d) {
		a = 1;
		b = msg.sender;
		c = true;
		d = 2;
	}
}
```

As shown in Listing \ref{listing\:chap6\_return-struct}, the `test()` function in the `TestContract` returns multiple values and has `internal` visibility. If the return values change, the function ABI (including hex signatures) must be updated, which is error-prone.

**Remediation:**
Create a `struct` type that contains all the return values, assign each value accordingly in the function, and return the struct. This approach centralizes and simplifies future modifications. The optimized version is shown in Listing \ref{listing\:chap6\_return-struct-fixed}.

```solidity
contract TestContract {
	struct ReturnStruct {
		uint a;
		address b;
		bool c;
		int d;
	}
	function test() internal returns(ReturnStruct memory) {
		ReturnStruct memory result;
		result.a = 1;
		result.b = msg.sender;
		result.c = true;
		result.d = 2;
		return result;
	}
}
```

---

#### (12) **External Function Visibility (`external-function`, EF)**

Functions declared as `public` but not called internally within the contract should be marked as `external`. This not only improves code readability but also reduces gas consumption when the function is called.

```solidity
contract ContractWithFunctionCalledSuper {
	uint256 aa = 0;
	function callWithSuper() public returns (uint256) {
		return aa;
	}
}
```

As shown in Listing \ref{listing\:chap6\_external-function}, the function `callWithSuper()` is not used internally and can therefore have its visibility changed to `external` to save gas.

**Remediation:**
Change the function’s visibility from `public` to `external` where internal calls are not required. The optimized contract is provided in Listing \ref{listing\:chap6\_external-function-fixed}.

```solidity
contract ContractWithFunctionCalledSuper {
	uint256 aa = 0;
	function callWithSuper() public returns (uint256) {
		return aa;
	}
}
```

---

### **Access Control**

Functions lacking proper access restrictions can lead to severe security vulnerabilities. Attackers may exploit these to manipulate critical components of a contract—executing unauthorized operations, stealing sensitive data, or disrupting functionality.

#### (1) **Suicidal (`suicidal`, SU)**

This issue arises when a contract allows unrestricted invocation of `selfdestruct` (or its alias `suicide`), enabling any user to destroy the contract and drain its balance due to missing or insufficient access control.

```solidity
contract Suicidal {
	mapping(address => uint) balance;
	function deploy() public payable {
		balance[msg.sender] += msg.value;
	}
	function kill() public {
		selfdestruct(msg.sender);
	}
}
```

As illustrated in Listing \ref{listing\:chap6\_suicidal}, a malicious user (e.g., Bob) can call the `kill()` function to destroy the contract and steal all the funds previously stored by other users.

**Remediation:**
Add access control to the sensitive `kill()` function. Specifically, declare an `owner` state variable in the `Suicidal` contract and initialize it within the constructor. Before executing the `selfdestruct` operation, insert a `require` statement to ensure that only the owner can invoke the function. The secured version of the contract is shown in Listing \ref{listing\:chap6\_suicidal-fixed}.

```solidity
contract Suicidal {
	mapping(address => uint) balance;
	address owner;
	function Suicidal() {
		owner = msg.sender;
	}
	function deploy() public payable {
		balance[msg.sender] += msg.value;
	}
	function kill() public {
		require(owner == msg.sender);
		selfdestruct(msg.sender);
	}
}
```

---

#### (2) **Arbitrary Send (`arbitrary-send`, AS)**

This vulnerability occurs when a contract allows Ether to be sent to arbitrary addresses without proper authorization. Anyone can exploit such a function to withdraw funds, resulting in loss of assets for legitimate users.

```solidity
contract ArbitrarySend {
	address public destination;
	mapping(address => uint) balance;
	function deploy() public payable {
		balance[msg.sender] += msg.value;
	}
	function setDestination() public {
		destination = msg.sender;
	}
	function withdraw() public {
		destination.transfer(address(this).balance);
	}
}
```

As shown in Listing \ref{listing\:chap6\_suicidal}, a user like Bob could exploit this by first calling `setDestination()` and then `withdraw()` to drain the entire contract balance, which was originally deposited by legitimate users through `deploy()`.

**Remediation:**
Restrict access to the sensitive `withdraw()` function. Declare an `owner` state variable in the `ArbitrarySend` contract and initialize it in the constructor. Use a `require` statement to verify the caller's identity before executing the `transfer` operation. The fixed version is presented in Listing \ref{listing\:chap6\_arbitrary-send-fixed}.

```solidity
contract ArbitrarySend {
	address public destination;
	mapping(address => uint) balance;
	address owner;
	function ArbitrarySend() {
		owner = msg.sender;
	}
	function deploy() public payable {
		balance[msg.sender] += msg.value;
	}
	function setDestination() public {
		destination = msg.sender;
	}
	function withdraw() public {
		require(owner == msg.sender);
		destination.transfer(address(this).balance);
	}
}
```

---

#### (3) **tx.origin Authentication (`tx-origin`, TO)**

Using `tx.origin` for authentication is insecure. If a legitimate user interacts with a malicious contract, the malicious contract can invoke the target contract (which uses `tx.origin` for access control) and bypass the intended security checks—resulting in theft of funds.

```solidity
contract TxOrigin {
	address public owner;
	mapping(address => uint) balance;
	constructor() public {
		owner = msg.sender;
	}
	function deploy() public payable {
		balance[msg.sender] += msg.value;
	}
	function withdraw_balance() public {
		require(tx.origin == owner);
		msg.sender.transfer(address(this).balance);
	}
}
```

As illustrated in Listing \ref{listing\:chap6\_tx-origin}, Bob is the owner of the `TxOrigin` contract and calls a seemingly safe function `safefunc()` from the `Eve` contract. However, as shown in Listing \ref{listing\:chap6\_tx-origin-attack}, `safefunc()` calls `withdraw_balance()` of the `TxOrigin` contract, which passes the `tx.origin` check and drains all the funds to `Eve`.

```solidity
contract Eve {
	TxOrigin txorigin;
	address owner;
	constructor(address txorigin_addr) public {
		owner = msg.sender;
		txorigin = TxOrigin(txorigin_addr);
	}
	function safefunc() public payable {
		txorigin.withdraw_balance();
	}
}
```
**Remediation:**
Replace `tx.origin` with `msg.sender` for authentication. This ensures only the direct caller’s identity is verified, preventing external contracts from impersonating users. The corrected contract is provided in Listing \ref{listing\:chap6\_tx-origin-fixed}.

```solidity
contract TxOrigin {
	address public owner;
	mapping(address => uint) balance;
	constructor() public {
		owner = msg.sender;
	}
	function deploy() public payable {
		balance[msg.sender] += msg.value;
	}
	function withdraw_balance() public {
		require(msg.sender == owner);
		msg.sender.transfer(address(this).balance);
	}
}
```

---

### **Transaction Dependence**

In Ethereum, the outcome of smart contract interactions can be affected by the order in which transactions are included in the same block. If contract logic depends on the sequence of independent transactions, it opens the door for **Transaction-Order Dependence (TOD)** attacks, where adversaries manipulate transaction order—typically by offering higher gas fees—to gain unfair advantages or steal user funds.

#### (1) **Transaction-Order Dependence (`tod`, TOD)**

This vulnerability arises when different functions within a contract interact with the same state variable, and the execution order of their respective transactions affects the contract’s behavior. Miners are incentivized to include transactions with higher gas prices first, which can be exploited by attackers.

```solidity
contract EthTxOrderDependence {
	address public owner;
	uint public reward;
	function EthTxOrderDependence() public payable {
		owner = msg.sender;
		reward = msg.value;
	}
	function setReward() public payable {
		require(msg.sender == owner);
		owner.transfer(reward);
		reward = msg.value;
	}
	function claimReward(uint256 submission) {
		require(submission < 10);
		msg.sender.transfer(reward);
	}
}
```

As shown in Listing \ref{listing\:chap6\_tod}, the `EthTxOrderDependence` contract has two functions, `setReward()` and `claimReward()`, both of which operate on the `reward` variable—one updates it, and the other reads its value to execute a reward transfer. A user may observe a high reward value and submit a transaction to `claimReward()`. However, the contract owner could submit a transaction calling `setReward()` with a much lower reward amount and a higher gas price. As a result, the miner is likely to include the owner’s transaction first, reducing the reward before the user’s claim is processed. The user receives less than expected.

**Remediation:**
Introduce a commitment mechanism to prevent the contract owner from changing the reward arbitrarily after users have seen it. Specifically, add a locking variable `setlock`. After the owner sets the reward via `setReward()`, they must call `lockReward()` to lock the reward value. Users can then verify that the reward is locked by calling `getlock()` before invoking `claimReward()`. If their claim is valid, the lock is reset to `false`, allowing a new reward round to begin. The mitigated contract is shown in Listing \ref{listing\:chap6\_tod-fixed}.

```solidity
contract EthTxOrderDependence {
	address public owner;
	uint public reward;
	bool public setlock=false;
	bool private setreward=false;
	function EthTxOrderDependence() public payable {
		owner = msg.sender;
		reward = msg.value;
	}
	function setReward() public payable {
		require (!setlock);
		require(msg.sender == owner);
		owner.transfer(reward);
		reward = msg.value;
		setreward = true;
	}
	function lockReward() public {
		require (setreward);
		require(msg.sender == owner);
		setlock = true;
		setreward = false;
	}
	function getlock() public returns (bool) {
		return setlock;
	}
	function claimReward(uint256 submission) {
		require (setlock);
		require(submission < 10);
		setlock = false;
		msg.sender.transfer(reward);
	}
}
```

---

### **Block Dependency**

Relying on block-specific attributes to generate randomness in smart contracts is insecure. Since miners and cooperating nodes have partial or full control over certain block parameters, attackers can exploit this control to manipulate pseudo-random outputs for their benefit.

#### (1) **Timestamp Dependency (`timestamp`, TS)**

A common vulnerability occurs when contracts use `block.timestamp` or `now` to generate random numbers. These values can be influenced by malicious miners or cooperative nodes to produce predictable results. Additionally, adversaries may deploy auxiliary contracts to precompute random values and gain unfair advantages during the same block.

```solidity
pragma solidity ^0.8.1;
contract Roulette {
	constructor() public payable {} // initially fund contract
	// fallback function used to make a bet
	function guess(uint _guessvalue) public {
		uint random = block.timestamp % 15;
		if(random == _guessvalue) { // winner
			payable(msg.sender).transfer(address(this).balance);
		}
	}
}
```

As shown in Listing \ref{listing\:chap6\_timestamp}, the `Roulette` contract generates random numbers based on the current block timestamp. An attacker colluding with a miner can issue a transaction calling `guess(uint)` during a block where `now % 15 == 0`, ensuring victory and draining the contract's balance.

Moreover, the attacker can deploy a helper contract like `RouletteAttack` (Listing \ref{listing\:chap6\_timestamp-attack}), which precomputes the correct guess using the same timestamp and then calls `guess()` within the same block. If the guessed value matches the computed `random`, the attack succeeds. The attacker can then call `withdraw()` to collect the funds.

```solidity
pragma solidity ^0.8.1;
contract RouletteAttack {
	address owner;
	constructor() public payable {owner = msg.sender;}
	function attack(Roulette roulette) public {
		uint answer = uint(block.timestamp % 15);
		roulette.guess(answer);
	}
	function withdraw() public returns (uint) {
		require(owner == msg.sender);
		payable(msg.sender).transfer(address(this).balance);
	}
}
```

**Remediation:**
Avoid using manipulable parameters like `timestamp`. Instead, integrate **Chainlink VRF (Verifiable Random Function)** to generate secure, tamper-resistant randomness. The patched contract (Listing \ref{listing\:chap6\_timestamp-fixed}) inherits from `VRFConsumerBase`, with `keyHash` and `fee` set in the constructor. Random numbers are requested via `requestRandomness()`, and the result is handled in `fulfillRandomness()`, where original game logic is executed securely.

```solidity
pragma solidity ^0.8.1;
import {VRFConsumerBase} from "@chainlink/contracts/src/v0.8/vrf/VRFConsumerBase.sol";
contract Roulette is VRFConsumerBase {
	uint guessvalue;
	bytes32 internal keyHash;
	uint256 internal fee;
	uint256 public randomResult;
	constructor(address _VRFCoordinator, address _LinkToken, bytes32 _keyHash, uint256 _fee) VRFConsumerBase(_VRFCoordinator, _LinkToken) public payable {
		keyHash = _keyHash;
		fee = _fee;
	} // initially fund contract
	function fulfillRandomness(bytes32 requestId, uint256 randomness) internal override {
		randomResult = randomness;
		uint random = randomResult;
		if(random == guessvalue) { // winner
			payable(msg.sender).transfer(address(this).balance);
		}
	}
	// fallback function used to make a bet
	function guess(uint _guessvalue) public {
		guessvalue = _guessvalue;
		requestRandomness(keyHash, fee);
	}
}
```

#### (2) **Block Parameter Dependency (`block-other-parameters`, BP)**

This vulnerability refers to using other block parameters such as `block.number`, `block.difficulty`, `blockhash`, or `block.gaslimit` as sources of randomness. Similar to the timestamp vulnerability, these values can be predicted or manipulated by miners, especially if the rewards are substantial.

```solidity
contract RouletteBlock {
	constructor() public payable {} // initially fund contract
	// fallback function used to make a bet
	function guess(uint _guessvalue) public {
		uint random = (blockhash(block.number - 1) * block.difficulty) % 15;
		if(random == _guessvalue) { // winner
			msg.sender.transfer(this.balance);
		}
	}
}
```

In Listing \ref{listing\:chap6\_block-other-parameters}, randomness is derived from `(block.number * block.difficulty) % 15 == 5`. An attacker can collaborate with a miner to craft a block satisfying this condition and execute a transaction transferring 10 Ether to the `Roulette` contract, ensuring a win. Similar to the timestamp-based attack, the adversary may deploy a helper contract (Listing \ref{listing\:chap6\_block-other-parameters-attack}) to compute the winning condition and trigger the exploit.

Because parameters like `block.number`, `block.difficulty`, and `blockhash` are miner-influenced, attackers may even lease mining hardware to mine many blocks rapidly, select favorable outcomes, and discard the rest (a practice known as **block reorganization or selfish mining**).

```solidity
pragma solidity ^0.8.0;
contract RouletteBlockAttack {
	address owner;
	constructor() public payable {owner = msg.sender;}
	function attack(RouletteBlock rouletteblock) public {
		uint answer = uint((blockhash(block.number - 1) * block.difficulty) % 15);
		rouletteblock.guess(answer);
	}
	function withdraw() public returns (uint) {
		require(owner == msg.sender);
		msg.sender.transfer(address(this).balance);
	}
}
```

**Remediation:**
As with the timestamp vulnerability, avoid using miner-controllable parameters. Use Chainlink VRF to generate provably fair and verifiable random numbers. The improved contract is shown in Listing \ref{listing\:chap6\_block-other-parameters-fixed}.

```solidity
pragma solidity ^0.8.0;
import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";
contract RouletteBlock is VRFConsumerBase {
	uint guessvalue;
	bytes32 internal keyHash;
	uint256 internal fee;
	uint256 public randomResult;
	constructor(address _VRFCoordinator, address _LinkToken, bytes32 _keyHash, uint256 _fee) VRFConsumerBase(_VRFCoordinator, _LinkToken) public payable {
		keyHash = _keyHash;
		fee = _fee;
	} // initially fund contract
	function fulfillRandomness(bytes32 requestId, uint256 randomness) internal override {
		randomResult = randomness;
		uint random = randomResult;
		if(random == guessvalue) { // winner
			payable(msg.sender).transfer(address(this).balance);
		}
	}
	// fallback function used to make a bet
	function guess(uint _guessvalue) public {
		guessvalue = _guessvalue;
		requestRandomness(keyHash, fee);
	}
}
```