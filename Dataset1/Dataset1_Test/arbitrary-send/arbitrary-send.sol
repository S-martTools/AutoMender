contract Arbitrarysend {
    mapping (address => uint) userBalance;
    
    function arbitrary_send_true4(address bb) public
    {
        uint cc = userBalance[msg.sender];
         
        msg.sender.send(cc);  
    }

    function addToBalance() payable{
        userBalance[msg.sender] += msg.value;
    }

    function() public payable{}
}