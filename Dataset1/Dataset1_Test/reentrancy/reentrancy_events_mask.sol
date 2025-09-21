pragma solidity ^0.4.24;  
contract C{

    function C() public payable {}

    function f(address cc) public{  
        cc.call.value(1)();  
    }

}


contract Test{
    event E();

    function bug(C c, address cc) public{  
        c.f(cc);  
        emit E();      
    }

    function ok(C c, address cc) public{  
        emit E();    
        c.f(cc);  
    }
}