const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("==================================================");
  console.log("🚀 Deploying DegreeSoulboundToken (SBT NFT)...");
  console.log("Deployer address:", deployer.address);
  console.log(
    "Deployer balance:",
    hre.ethers.formatEther(await hre.ethers.provider.getBalance(deployer.address)),
    "ETH"
  );
  console.log("==================================================");

  const DegreeSBT = await hre.ethers.getContractFactory("DegreeSoulboundToken");
  const contract = await DegreeSBT.deploy();
  await contract.waitForDeployment();
  const address = await contract.getAddress();

  console.log("\n✅ DegreeSoulboundToken deployed at:", address);
  console.log("\n👉 Hướng dẫn tích hợp:");
  console.log("   1. Cập nhật SBT_CONTRACT_ADDRESS=" + address + " vào file .env");
  console.log("   2. Sinh viên có thể add contract này vào ví MetaMask tab NFTs để xem văn bằng.");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
