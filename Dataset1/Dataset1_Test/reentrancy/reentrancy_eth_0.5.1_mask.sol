pragma solidity ^0.5.0;  

contract Reentrancy {
    mapping (address => uint) userBalance;  
   
    function getBalance(address u) view public returns(uint){  
        return userBalance[u];
    }

    function addToBalance() payable public{  
        userBalance[msg.sender] += msg.value;  
    }   

    function withdrawBalance() public{  
         
         
        (bool ret, bytes memory mem) = msg.sender.call.value(userBalance[msg.sender])("");   
        if( ! ret ){  
            revert();
        }
        userBalance[msg.sender] = 0;  
    }   

    function withdrawBalance_fixed() public{  
         
         
        uint amount = userBalance[msg.sender];
        userBalance[msg.sender] = 0;
        (bool ret, bytes memory mem) = msg.sender.call.value(amount)("");  
        if( ! ret ){  
            revert();
        }
    }   

    function withdrawBalance_fixed_2() public{  
         
         
         
         
        msg.sender.transfer(userBalance[msg.sender]);  
        userBalance[msg.sender] = 0;  
    }   
   
    function withdrawBalance_fixed_3() public{  
         
         
        uint amount = userBalance[msg.sender];
        userBalance[msg.sender] = 0;
        (bool ret, bytes memory mem) = msg.sender.call.value(amount)("");  
        if( ! ret ){
            userBalance[msg.sender] = amount;  
        }
    }   
}