const hre = require("hardhat");
async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying DegreeVerification v2...");
  console.log("Deployer address:", deployer.address);
  console.log(
    "Deployer balance:",
    hre.ethers.formatEther(await hre.ethers.provider.getBalance(deployer.address)),
    "ETH"
  );
  const DegreeVerification = await hre.ethers.getContractFactory("DegreeVerification");
  const contract = await DegreeVerification.deploy();
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  console.log("\n✅ DegreeVerification deployed at:", address);
  console.log("\n👉 Các bước tiếp theo:");
  console.log("   1. Cập nhật CONTRACT_ADDRESS=" + address + " vào file .env");
  console.log("   2. Verify: npx hardhat verify --network sepolia", address);
  console.log("   3. Gọi addIssuer(<địa_chỉ_ví_issuer>) để cấp quyền cho cán bộ");
}
main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});