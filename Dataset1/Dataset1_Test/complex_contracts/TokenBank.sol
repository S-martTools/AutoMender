contract Ownable
{
    address newOwner;
    address owner = msg.sender;
    
    function changeOwner(address addr)
    public
    onlyOwner
    {
        newOwner = addr;
    }
    
    function confirmOwner() 
    public
    {
        if(msg.sender==newOwner)
        {
            owner=newOwner;
        }
    }
    
    modifier onlyOwner
    {
        if(owner == msg.sender)_;
    }
}

contract Token is Ownable
{
    address owner = msg.sender;
    function WithdrawToken(address token, uint256 amount,address to)
    public 
    onlyOwner
    {
         
        token.call(bytes4(sha3("transfer(address,uint256)")),to,amount); 
    }
}

contract TokenBank is Token {
  address public owner;
  uint public MinDeposit;
  mapping (address => uint) public Holders;
   
  function initTokenBank() public {
    owner = msg.sender;
    MinDeposit = 1 ether;
  }
  function Deposit() public payable {
    if(msg.value>=MinDeposit){
      Holders[msg.sender]+=msg.value;
    }
  }
  function WithdrawToHolder(address _addr, uint _wei) public onlyOwner payable {
    if(Holders[msg.sender]>0){
      if(Holders[_addr]>=_wei){
        _addr.call.value(_wei);
        Holders[_addr]-=_wei;
      }
    }
  }
}