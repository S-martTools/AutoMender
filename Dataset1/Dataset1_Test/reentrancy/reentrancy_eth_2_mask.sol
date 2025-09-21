pragma solidity ^0.4.24;  

contract Reentrancy {
    mapping (address => uint) userBalance;  
   
    function getBalance(address u) view public returns(uint){  
        return userBalance[u];
    }

    function addToBalance() payable public{  
        userBalance[msg.sender] += msg.value;  
    }

    function withdrawBalance() public{  
         
         
        if( ! (msg.sender.call.value(userBalance[msg.sender])() ) ){  
            revert();
        }
        userBalance[msg.sender] = 0;  
    }   

    function withdrawBalance_bad2() public{  
         
         
        require(msg.sender.call.value(userBalance[msg.sender])());  
        userBalance[msg.sender] = 0;  
    } 

    function withdrawBalance_bad3() public{  
         
         
        msg.sender.call.value(userBalance[msg.sender])();  
        userBalance[msg.sender] = 0;  
    }   


    function withdrawBalance_good() public{  
         
         
        if( ! (msg.sender.send(userBalance[msg.sender]) ) ){  
            revert();
        }
        userBalance[msg.sender] = 0;  
    }

    function withdrawBalance_good1() public{  
         
         
	if(userBalance[msg.sender]>1)
	{
            if( ! (msg.sender.call.value(0)() ) ){  
                revert();
            }
	    userBalance[msg.sender] = userBalance[msg.sender] - 1;  
	}      
    }

    function withdrawBalance_good2() public{  
         
         
	if(userBalance[msg.sender]>1)
	{
	    uint aa = 0;
            if( ! (msg.sender.call.value(aa)() ) ){  
                revert();
            }
	    userBalance[msg.sender] = userBalance[msg.sender] - aa;  
	}      
    }

    function withdrawBalance_fixed() public{  
         
         
        uint amount = userBalance[msg.sender];
        userBalance[msg.sender] = 0;
        if( ! (msg.sender.call.value(amount)() ) ){  
            revert();
        }
    }   

    function withdrawBalance_fixed_1() public{  
         
         
         
         
        msg.sender.transfer(userBalance[msg.sender]);  
        userBalance[msg.sender] = 0;  
    }

    function withdrawBalance_fixed_2() public{  
         
         
         
         
        msg.sender.transfer(0);  
        userBalance[msg.sender] = userBalance[msg.sender] - 0;  
    }   
   
    function withdrawBalance_fixed_5() public{  
         
         
         
         
	uint aa = 0;
        msg.sender.transfer(aa);  
        userBalance[msg.sender] = userBalance[msg.sender] - aa;  
    }   

    function withdrawBalance_fixed_3() public{  
         
         
        uint amount = userBalance[msg.sender];
        userBalance[msg.sender] = 0;
        if( ! (msg.sender.call.value(amount)() ) ){  
            userBalance[msg.sender] = amount;
        }
    }   
    function withdrawBalance_fixed_4() public{  
         
         
        uint amount = userBalance[msg.sender];
        userBalance[msg.sender] = 0;
        if( (msg.sender.call.value(amount)() ) ){  
            return;
        }
        else{
            userBalance[msg.sender] = amount;
        }
    }   

    function withdrawBalance_nested() public{  
        uint amount = userBalance[msg.sender];
        if( msg.sender.call.value(amount/2)() ){  
            msg.sender.call.value(amount/2)();  
            userBalance[msg.sender] = 0;  
        }
    }   

}