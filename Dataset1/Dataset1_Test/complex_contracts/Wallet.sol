pragma solidity ^0.5.0; 
contract Wallet {
  mapping(address => uint) balance;
   
  function deposit(uint amount) public payable {
    require(msg.value == amount, 'msg.value must be equal to amount');
    balance[msg.sender] = amount;
  }
   
  function withdraw(uint amount) public {
    require(amount <= balance[msg.sender], 'amount must be less than balance');
    uint previousBalance = balance[msg.sender];
    balance[msg.sender] = previousBalance - amount; 
     
    msg.sender.call.value(amount);
  }
}