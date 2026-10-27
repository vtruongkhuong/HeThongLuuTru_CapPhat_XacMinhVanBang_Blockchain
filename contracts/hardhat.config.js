require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: ".env" });
/** @type {import('hardhat/config').HardhatUserConfig} */
module.exports = {
    solidity: {
        version: "0.8.20",
        settings: {
            optimizer: { enabled: true, runs: 200 },
        },
    },
    networks: {
        // Mạng local để test nhanh (không cần MetaMask)
        hardhat: {},
        // Sepolia Testnet – dùng để deploy thật
        sepolia: {
            url: process.env.WEB3_PROVIDER_URL || "https://rpc.sepolia.org",
            accounts: process.env.DEPLOY_PRIVATE_KEY
                ? [process.env.DEPLOY_PRIVATE_KEY]
                : [],
            chainId: 11155111,
        },
    },
    // Verify trên Etherscan (chạy: npx hardhat verify --network sepolia <ADDRESS>)
    etherscan: {
        apiKey: process.env.ETHERSCAN_API_KEY || "",
    },
};