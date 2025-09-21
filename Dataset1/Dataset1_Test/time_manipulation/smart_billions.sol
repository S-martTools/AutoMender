pragma solidity ^0.4.13;

 
contract SmartBillions {

     
    string constant name = "SmartBillions Token";
    string constant symbol = "PLAY";
    uint constant decimals = 0;

     
    struct Wallet {
        uint208 balance;  
    	uint16 lastDividendPeriod;  
    	uint32 nextWithdrawBlock;  
    }
    mapping (address => Wallet) wallets;
    struct Bet {
        uint192 value;  
        uint32 betHash;  
        uint32 blockNum;  
    }
    mapping (address => Bet) bets;

    uint walletBalance = 0;  

     
    uint investStart = 1;  
    uint investBalance = 0;  
    uint investBalanceMax = 200000 ether;  
    uint dividendPeriod = 1;
    uint[] dividends;  

     
    uint maxWin = 0;  
    uint hashFirst = 0;  
    uint hashLast = 0;  
    uint hashNext = 0;  
    uint hashBetSum = 0;  
    uint hashBetMax = 5 ether;  
    uint[] hashes;  

     
     
    uint constant hashesSize = 16384 ;  
    uint coldStoreLast = 0 ;  

    function calcHashes(uint32 _lastb, uint32 _delta) public returns (uint) {
         
        return( ( uint(block.blockhash(_lastb  )) & 0xFFFFFF )
         
            | ( ( uint(block.blockhash(_lastb+1)) & 0xFFFFFF ) << 24 )
             
            | ( ( uint(block.blockhash(_lastb+2)) & 0xFFFFFF ) << 48 )
             
            | ( ( uint(block.blockhash(_lastb+3)) & 0xFFFFFF ) << 72 )
             
            | ( ( uint(block.blockhash(_lastb+4)) & 0xFFFFFF ) << 96 )
             
            | ( ( uint(block.blockhash(_lastb+5)) & 0xFFFFFF ) << 120 )
             
            | ( ( uint(block.blockhash(_lastb+6)) & 0xFFFFFF ) << 144 )
             
            | ( ( uint(block.blockhash(_lastb+7)) & 0xFFFFFF ) << 168 )
             
            | ( ( uint(block.blockhash(_lastb+8)) & 0xFFFFFF ) << 192 )
             
            | ( ( uint(block.blockhash(_lastb+9)) & 0xFFFFFF ) << 216 )
            | ( ( uint(_delta) / hashesSize) << 240));
    }
}