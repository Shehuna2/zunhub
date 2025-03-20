// SPDX-License-Identifier: MIT

pragma solidity 0.8.18;


import "./simpleStorage.sol";

contract storageFactory {

    SimpleStorage[] public listOfSimpleStorageContracts;

    function createSimpleStorageFactory() public {
        SimpleStorage newSimpleStorageContracts = new SimpleStorage();
        listOfSimpleStorageContracts.push(newSimpleStorageContracts);
    }
}