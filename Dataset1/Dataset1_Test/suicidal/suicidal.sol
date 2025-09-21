contract C {
    address owner;

    function init() public {
        owner = msg.sender;  
    }

    function false_selfdestruct() public{
        require(msg.sender == owner);
        selfdestruct(msg.sender);
    }

    function false_selfdestruct1() public{
        selfdestruct(msg.sender);
    }

    function false_selfdestruct2() public{
        selfdestruct(msg.sender);
    }

    function false_selfdestruct3() public{
        selfdestruct(msg.sender);
    }

    function false_selfdestruct4() public{
        selfdestruct(msg.sender);
    }
}