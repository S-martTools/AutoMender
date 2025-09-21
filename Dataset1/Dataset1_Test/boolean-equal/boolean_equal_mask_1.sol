contract MyConc{

    bool flag6;  
    int a;
    bool flag4 = false;  
    function MyConc()  
    {
		a = 4;
		flag6 = false;
    }

    function bad11(bool flag) external{
        bool flag7 = true && false;  
        bool flag8 = 1 >= 0;  
		bool flag9 = flag7 || flag8;  
		if(flag == flag9){}  
    }
    function bad12(bool flag) external{
    	bool flag2 = true;
		bool flag10 = !flag2;  
		if(flag == flag10){}  
    }

    function good(bool flag) external{
        if(flag){
			 
		}
    }

    function badrequire(bool flag) external{
        require(flag == true);
    }

    function badrequire1(bool flag) external{
        require(flag == false);
    }

    function badrequire2(bool flag) external{
        require(flag == true);
    }

    function badrequire3(bool flag) external{
        require(flag == false);
    }

    function good1(bool flag) external{
        bool flag1 = flag;
        while(flag1){  
		    flag1 = false;
		}
    }

    function badreassert(bool flag) external{
        assert(flag == true);
    }

    function badreassert1(bool flag) external{
        assert(flag == false);
    }

    function badreassert2(bool flag) external{
        assert(flag == true);
    }

    function badreassert3(bool flag) external{
        assert(flag == false);
    }

    function good2(bool flag) external{      
		require(flag);
    }
    function good3(bool flag) external{
		assert(flag);  
    }

}