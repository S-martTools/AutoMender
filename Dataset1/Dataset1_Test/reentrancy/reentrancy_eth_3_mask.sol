pragma solidity ^0.4.24;  

contract Called{
    function f() public;  
    uint counter = 0;  
    function callme() payable{  
        if( counter < 2 && ! (msg.sender.call.value(1)() ) ){  
            throw;  
        }
        counter += 1;  
    }
}

contract ReentrancyEvent {

    mapping (address => uint) userBalance;  

    event E();

    function test_4() public payable{  
	uint aa = 0;
        msg.sender.call.value(aa)();  
        emit E();  
    }

    function test_1() public{  
	uint aa = 0;
        msg.sender.transfer(aa);  
	userBalance[msg.sender] = userBalance[msg.sender] - aa;  
        emit E();  
    }   

    function test_2() public{  
	uint amount = userBalance[msg.sender];
        userBalance[msg.sender] = 0;
        if( ! (msg.sender.call.value(amount)() ) ){  
            userBalance[msg.sender] = amount;
        }
        emit E();  
    }  

    function test_5() public{  
	uint amount = userBalance[msg.sender];
        userBalance[msg.sender] = 0;
        if( ! (msg.sender.send(amount) ) ){  
            userBalance[msg.sender] = amount;
        }
        emit E();  
    }

    function test_3() public{  
	if( ! (msg.sender.send(userBalance[msg.sender]) ) ){  
            revert();
        }
        userBalance[msg.sender] = 0;
        emit E();  
    }  
}