// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BAK-Coin (BAK)
 * @dev BEP-20 Token for BAK Remittance
 * @dev Supply: 21,000,000 BAK
 * @dev Symbol: BAK
 * @dev Name: BAK-Coin
 */

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BAKCoin is ERC20, Ownable {
    uint256 public constant MAX_SUPPLY = 21_000_000 * 10**18;

    constructor() ERC20("BAK-Coin", "BAK") Ownable(msg.sender) {
        _mint(msg.sender, MAX_SUPPLY);
    }

    function decimals() public pure override returns (uint8) {
        return 18;
    }

    // لا يمكن طبع المزيد
    function mint(address to, uint256 amount) public onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "BAK: exceeds max supply");
        _mint(to, amount);
    }
}
