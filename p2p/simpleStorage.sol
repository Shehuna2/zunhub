// SPDX-License-Identifier: MIT
pragma solidity 0.8.18;

contract simpleStorage {
    uint256 favoriteNumber;

    function store(uint256 _favoriteNumber) public {
        favoriteNumber = _favoriteNumber;
    }

    function retrieve() public view returns (uint256){
        return favoriteNumber;
    }
        
        
    
}