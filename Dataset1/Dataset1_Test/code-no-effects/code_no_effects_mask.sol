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

     
    function withdraw_bad1(uint amount) public {  
        require(amount <= balance[msg.sender], 'amount must be less than balance');

        uint previousBalance = balance[msg.sender];
        balance[msg.sender] = previousBalance - amount;  

        address withdraw_address = msg.sender;  

         
        withdraw_address.call.value(amount);  
    }

    function withdraw_bad2(uint amount) public {  
        require(amount <= balance[msg.sender], 'amount must be less than balance');

        balance[msg.sender] = balance[msg.sender] - amount;  

        address withdraw_address = msg.sender;  

         
        withdraw_address.call.value(amount);  
    }
}