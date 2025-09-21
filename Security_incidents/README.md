# The Examples of Defective Wild Contracts

To demonstrate the effectiveness of AutoMender, we apply it to public bug incident contracts from Dataset\_3. 

## Security Incident Contract Examples


The fixes of the SmartMesh (SMT) incident contract.
```
  mapping (address => uint256) balances;
  function transferProxy(uint256 _value, uint256 _feeSmt,...) public ...{
-   if(balances[_from]<_feeSmt+_value) revert();
+   require(_feeSmt+_value>=_value && balances[_from]>=_feeSmt+_value);
    Transfer(_from, msg.sender, _feeSmt);
    ...
  }
```

The fixes of the BEC incident contract.
```
  mapping(address => uint256) balances;
  function batchTransfer(address[] _receivers, uint256 _value) ... {
-   uint256 amount=uint256(_receivers.length) * _value;
+   uint256 amount=uint256(_receivers.length).mul(_value);
    require(_value>0 && balances[msg.sender]>=amount);
    balances[msg.sender]=balances[msg.sender].sub(amount);
    ...
  } 
```

**The SmartMesh (SMT) incident contract.** In April 2018, the SMT contract suffered attacks and was suspended by various platforms such as Ethereum. Specifically, as shown in above code, attackers can manipulate the input parameter of the function ``transferProxy(uint256,...)'' to make \_fee+\_value=0 (*integer-overflow* bug occurred), so that the verification in line 3 can be passed and attackers can obtain plenty of money. Also, this line contains a *revert-require* optimization. Given the enhanced context understanding capabilities, AutoMender replaced the *require* statement and added the judgment of calculated results in the conditions, so as to fix these two issues simultaneously. 
Although contracts such as *BEC* validated the arithmetic variables in line 4 of above code, the ineffective operations still caused the *integer-overflow* bug in line 3. 
To this end, AutoMender directly replaced the multiplication operation with the *SafeMath* library to minimize code changes, which is already declared and used in line 6. 
However, these modifications cannot be performed by the current methods such as Two Timin' \cite{CoRR_Timin}, which should be further enhanced with the refined reasoning and repair quality constraints. 