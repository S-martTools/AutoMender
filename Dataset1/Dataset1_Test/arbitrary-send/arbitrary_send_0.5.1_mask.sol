pragma solidity ^0.5.1;
contract Test{

    address payable destination;  

    mapping (address => uint) balances;  

    constructor() payable public{
        balances[msg.sender] = 0;
    }

    function direct() public{  
        msg.sender.send(address(this).balance);  
    }

    function init() public{  
        destination = msg.sender;  
    }

    function indirect() public{  
        destination.send(address(this).balance);
    }

    function nowithdraw() public{  
        uint val = balances[msg.sender];
        balances[msg.sender] = 0;
        msg.sender.send(val);  
    }

    function buy() payable public{  
        uint value_send = msg.value;  
        uint value_spent = 0 ;  
        uint remaining = value_send - value_spent;  
        msg.sender.send(remaining);  
}

}