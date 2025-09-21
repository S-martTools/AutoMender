def normalized_levenshtein(a: str, b: str) -> float:
    if a==b: return 0.0
    dp=[[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1): dp[i][0]=i
    for j in range(len(b)+1): dp[0][j]=j
    for i in range(1,len(a)+1):
        for j in range(1,len(b)+1):
            cost=0 if a[i-1]==b[j-1] else 1
            dp[i][j]=min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
    return dp[-1][-1]/max(len(a),len(b))
def gas_struct_score(orig_code: str, patched_code: str, leven_threshold: float=0.4) -> float:
    lev=normalized_levenshtein(orig_code, patched_code)
    return max(0.0, 1.0 - lev/leven_threshold)
