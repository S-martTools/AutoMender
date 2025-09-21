pragma solidity ^0.8.1;
contract EtherLotto {		
    uint TICKET_AMOUNT = 10;  
    uint FEE_AMOUNT = 1;  
    address payable public bank;  
    uint public pot;  
     
    constructor() public payable {
        bank = payable(msg.sender);
    }
     
    function play() public payable {
         
        assert(msg.value == TICKET_AMOUNT);
         
        pot += msg.value;	
         
        uint random = uint(keccak256(abi.encodePacked(block.timestamp))) % 2;
        if (random == 0) {	
            bank.call{value: FEE_AMOUNT}("");  
            msg.sender.call{value: pot - FEE_AMOUNT}("");  
            pot = 0;  
        }
    }
}