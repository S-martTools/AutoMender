contract Arbitrarysend {

    function Arbitrarysend() payable {
    }
    
    function arbitrary_send_true4(address bb) public
    {
        msg.sender.send(1 ether);  
    }

}