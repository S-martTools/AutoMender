contract ContractWithBaseFunctionCalled {
    function getsCalledByBase() public;  
    function callsOverrideMe() external {
        getsCalledByBase();
    }
}


contract DerivingContractWithBaseCalled is ContractWithBaseFunctionCalled {
    function getsCalledByBase() public {  
         
    }
}


 
contract ContractWithDynamicCall {
    function() returns(uint) ptr;  

    function test1() public returns(uint){  
        return 1;
    }

    function test2() public returns(uint){  
        return 2;
    }

    function setTest1() external{
        ptr = test1;  
    }

    function setTest2() external{
        ptr = test2;  
    }

    function exec() external returns(uint){
        return ptr();
    }
}

contract DerivesFromDynamicCall is ContractWithDynamicCall{
    function getsCalledDynamically() public returns (uint){  
         
        return 3;
    }
    function setTest3() public {  
         
         

        ptr = getsCalledDynamically;  
    }
}