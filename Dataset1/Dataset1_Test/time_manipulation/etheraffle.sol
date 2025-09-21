pragma solidity ^0.4.16;

contract Ethraffle_v4b {
    struct Contestant {
        address addr;
        uint raffleId;
    }

    event RaffleResult(
        uint raffleId,
        uint winningNumber,
        address winningAddress,
        address seed1,
        address seed2,
        uint seed3,
        bytes32 randHash
    );

    event TicketPurchase(
        uint raffleId,
        address contestant,
        uint number
    );

    event TicketRefund(
        uint raffleId,
        address contestant,
        uint number
    );

     
    uint constant prize = 2.5 ether;
    uint constant fee = 0.03 ether;
    uint constant totalTickets = 1;
    uint constant pricePerTicket = (prize + fee) / totalTickets;  
    address feeAddress;

     
    bool paused = false;
    uint raffleId = 1;
     
    uint blockNumber = block.number % 2;
    uint blockNumber_copy = blockNumber;
    uint nextTicket = 0;
    mapping (uint => Contestant) contestants;
    uint[] gaps;

     
    function Ethraffle_v4b() public {
        feeAddress = msg.sender;
    }

    function buyTickets() payable public {
        
        uint moneySent = msg.value;

	uint currTicket = 0;
        contestants[currTicket] = Contestant(msg.sender, raffleId);
    }

    function chooseWinner() public {
         
        address seed1 = contestants[uint(block.coinbase) % totalTickets].addr;
         
        address seed2 = contestants[uint(msg.sender) % totalTickets].addr;
         
        uint seed3 = block.difficulty;
        bytes32 randHash = keccak256(seed1, seed2, seed3);

        uint winningNumber = uint(randHash) % totalTickets;
    }

}