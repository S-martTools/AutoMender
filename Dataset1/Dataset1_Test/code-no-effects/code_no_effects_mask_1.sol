pragma solidity ^0.5.0;  

contract Wallet {
    mapping(address => uint) balance;  

    function withdraw_bad3(uint amount) public {  
        require(amount <= balance[msg.sender], 'amount must be less than balance');

        balance[msg.sender] = balance[msg.sender] - amount;  

        address withdraw_address = msg.sender;  

         
        withdraw_address.call.value(amount);  
    }

    function withdraw_bad4(uint amount) public {  
        require(amount <= balance[msg.sender], 'amount must be less than balance');

        balance[msg.sender] = balance[msg.sender] - amount;  

        address withdraw_address = msg.sender;  

         
        withdraw_address.call.value(amount);  
    }

    function withdraw_bad5(uint amount) public {  
        require(amount <= balance[msg.sender], 'amount must be less than balance');

        uint previousBalance = balance[msg.sender];
        balance[msg.sender] = previousBalance - amount;  

        address withdraw_address = msg.sender;  

         
        withdraw_address.call.value(amount);  
    }

    function withdraw_bad6(uint amount) public {  
        require(amount <= balance[msg.sender], 'amount must be less than balance');

        uint previousBalance = balance[msg.sender];
        balance[msg.sender] = previousBalance - amount;  

        address withdraw_address = msg.sender;  

         
        withdraw_address.call.value(amount);  
    }

    function withdraw_bad7(uint amount) public {  
        require(amount <= balance[msg.sender], 'amount must be less than balance');
        balance[msg.sender] = balance[msg.sender] - amount;  
        msg.sender.call.value(amount);  
    }

     
    function withdraw_good(uint amount) public {  
        require(amount <= balance[msg.sender], 'amount must be less than balance');

        uint previousBalance = balance[msg.sender];
        balance[msg.sender] = previousBalance - amount;  

         
        (bool success, ) = msg.sender.call.value(amount)("");  
        require(success, 'transfer failed');
    }
}