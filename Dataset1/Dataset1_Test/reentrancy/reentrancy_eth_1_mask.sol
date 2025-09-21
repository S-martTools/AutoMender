contract NEW{
	mapping (address => uint) private userBalances;  
	mapping (address => bool) private claimedBonus;  
	mapping (address => uint) private rewardsForA;  

	function withdraw(address recipient) public payable {  
		uint amountToWithdraw = userBalances[recipient];
		rewardsForA[recipient] = 0;  
		if (!(recipient.call.value(amountToWithdraw)())) { throw; }  
	}

	function getFirstWithdrawalBonus(address recipient) public {  
		if (claimedBonus[recipient]) { throw; }  

		rewardsForA[recipient] += 100;  
		withdraw(recipient);  
		claimedBonus[recipient] = true;  
	}
}