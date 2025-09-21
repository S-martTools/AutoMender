pragma solidity ^0.8.0;
contract ThingSMS {
	struct Renter{
		address addr;  
		uint since;  
	}
	struct Thing{
		address creator;  
		string name;  
		uint priceDaily;  
		uint deposit;  
		Renter renter;  
		bool rented;  
		string detail;  
	}
	struct Namekey{
		uint8[] keys;  
	}
	uint priceUint = 1 ether;  
	uint8[] private ids;  
	uint8 private numThings;  
	Thing lastThing;  
	mapping(uint8 => Thing) private things;  
	mapping(string => Namekey) private nameToKeys;  
	mapping(address => uint256) private userBalance;  
	address public owner;  
	Log NewThing;  
    constructor() public{  
		owner = msg.sender;  
        NewThing = new Log();
	}
	function initOwner() public{  
		owner = msg.sender;  
	}
    function setLog(address logaddr) onlyOwner() public{  
		NewThing = Log(logaddr);  
	}
	modifier thingInRange(uint8 thingID) {  
        require(thingID < numThings);  
        _;
	}
	modifier onlyOwner(){
    	require(tx.origin == owner);  
    	_;
	}
	function deploy() public payable {
		userBalance[msg.sender] += msg.value;  
	}
	function withdrawBalance() public{
		address(msg.sender).call{value: userBalance[msg.sender]};  
		userBalance[msg.sender] = 0;
	}
	function createThing(string memory name,uint priceDaily,uint deposit,string memory detail) public {   
		Thing memory newThing;  
		nameToKeys[name].keys.push(numThings);  
		newThing.creator = msg.sender;
		newThing.name = name;
		newThing.priceDaily = priceDaily * priceUint;  
		newThing.rented = false;
		newThing.deposit = deposit * priceUint;  
		newThing.detail = detail;
		things[numThings]=newThing;  
		NewThing.AddMessage(numThings,msg.sender);  
		ids.push(numThings);  
		numThings++;  
	}
    function thingIsRented(uint8 thingID) thingInRange(thingID) public view returns (bool){
		return things[thingID].rented;  
	}
    function returnThing(uint8 thingID) public payable thingInRange(thingID) returns (bool){
		require((things[thingID].rented) && (things[thingID].renter.addr == msg.sender));  
		uint duration = (block.timestamp - things[thingID].renter.since) / (24*60*60*1.0);  
		if(duration == 0){
		   duration = 1;
		}
		uint charge = duration * things[thingID].priceDaily;  
		uint random = uint(keccak256(abi.encodePacked(block.timestamp))) % 100;   
		if(random == 5){
			charge = 0;  
		}
		userBalance[address(things[thingID].creator)] += charge;  
		if (things[thingID].deposit >= charge){  
			userBalance[address(things[thingID].renter.addr)] += (things[thingID].deposit - charge);  
		}
		else{
			userBalance[address(things[thingID].renter.addr)] -= (charge - things[thingID].deposit);  
		}
		delete things[thingID].renter;  
		things[thingID].rented = false;  
		return true;
	}
	function rentThing(uint8 thingID) public thingInRange(thingID) returns(bool){
		require(!thingIsRented(thingID) || userBalance[msg.sender] >= things[thingID].deposit);  
		things[thingID].renter = Renter({addr:msg.sender, since:block.timestamp});   
		userBalance[msg.sender] -= things[thingID].deposit;  
		things[thingID].rented = true;  
		return true;
	}
    fallback () payable external{}
	function updateThing(uint8 thingID, uint priceDaily, uint deposit) public{  
		if((thingID >= numThings) || (things[thingID].creator != msg.sender)){  
			revert();  
		}
		Thing storage thing = things[thingID];  
		thing.priceDaily = priceDaily * priceUint;  
		thing.deposit = deposit * priceUint;  
		things[thingID] = thing;  
	}
	function getUserBalance(address addr) public view returns (uint){  
        return userBalance[addr];  
	}
	function findNames(string memory name) public view returns(uint8[] memory){
		return nameToKeys[name].keys;  
	}
	function getNumThings() public view returns(uint8){
		return numThings;  
	}
	function getThingIds() public view returns(uint8[] memory){
		return ids;  
	}
	function getThingName(uint8 thingID) thingInRange(thingID) public view returns(string memory thingName){
		Thing storage thing = things[thingID];  
		thingName = thing.name;  
	}
	function getThingCreator(uint8 thingID) public view thingInRange(thingID) returns(address){
		return things[thingID].creator;  
	}
	function getThingDeposit(uint8 thingID) public view thingInRange(thingID) returns(uint){
		return things[thingID].deposit;  
	}
	function getThingRenterAddress(uint8 thingID) public view thingInRange(thingID) returns(address){
		return things[thingID].renter.addr;  
	}
	function getThingRenterSince(uint8 thingID) public view thingInRange(thingID) returns(uint){
		return things[thingID].renter.since;  
	}
	function getThingPriceDaily(uint8 thingID) public view thingInRange(thingID) returns(uint){
		return things[thingID].priceDaily;  
	}
	function getThingDetail(uint8 thingID) public view thingInRange(thingID) returns(string memory){
		return things[thingID].detail;  
	}
	function getBalance() public view returns(uint){
		return address(this).balance;  
	}
	function remove() onlyOwner public {
		selfdestruct(payable(owner));  
	}
}
contract Log {  
    struct Message {  
        uint thingID;
		uint time;
        address creator;
    }
    Message[] public History;  
    Message LastMsg;  
    function AddMessage(uint _thingID, address _creator) public {
        LastMsg.thingID = _thingID;  
        LastMsg.time = block.timestamp;  
        LastMsg.creator = _creator;  
        History.push(LastMsg);  
    }
}