pragma solidity ^0.4.24;  

contract CostlyOperationsInLoop{
  
  uint loop_count = 100;                                                                                           
  uint state_variable=0;  
  mapping (uint=>uint) map;   
  uint[100] arr;  
  
  function bad() external{                                                                                      
    for (uint i=0; i < loop_count; i++){  
      state_variable++;                                                                                      
    }                                                                                                        
  }
  function bad1() external{                                                                                      
    for (uint i=0; i < loop_count; i++){  
      state_variable++;                                                                                      
    }                                                                                                        
  }
  function bad2() external{                                                                                      
    for (uint i=0; i < loop_count; i++){  
      state_variable++;                                                                                      
    }                                                                                                        
  }
  function bad3() external{                                                                                      
    for (uint i=0; i < loop_count; i++){  
      state_variable++;                                                                                      
    }                                                                                                        
  }
  function bad4() external{                                                                                      
    for (uint i=0; i < loop_count; i++){  
      state_variable++;                                                                                      
    }                                                                                                        
  }
  function bad5() external{                                                                                      
    for (uint i=0; i < loop_count; i++){  
      state_variable++;                                                                                      
    }                                                                                                        
  }
  function bad6() external{                                                                                      
    for (uint i=0; i < loop_count; i++){  
      state_variable++;                                                                                      
    }                                                                                                        
  }
}