contract C{
    address owner;  

    function i_am_a_backdoor() public{  
        selfdestruct(msg.sender);  
    }

    function selfdestruct_1() public{  
        address aa = msg.sender;
        selfdestruct(msg.sender);  
    }

     
	 
     

    function good_selfdestruct() public{  
    	address aa = msg.sender;
    	require(aa == owner);
        selfdestruct(msg.sender);  
    }
}