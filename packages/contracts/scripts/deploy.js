const { ethers, network, run } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log("Deployer:", deployer.address);
  console.log("Balance :", ethers.formatEther(balance), "ETH");
  console.log("Network :", network.name, "(chainId:", (await ethers.provider.getNetwork()).chainId + ")");

  const restricted = false; // MVP: open submissions from the backend key
  const Factory = await ethers.getContractFactory("ImpactAnchor");
  const contract = await Factory.deploy(deployer.address, restricted);
  await contract.waitForDeployment();

  const addr = await contract.getAddress();
  console.log("ImpactAnchor deployed to:", addr);
  console.log("\nSet in your .env:");
  console.log("  ANCHOR_CONTRACT_ADDRESS=" + addr);

  if (network.name !== "hardhat" && process.env.BASESCAN_API_KEY) {
    console.log("\nWaiting 30s before verification...");
    await new Promise((r) => setTimeout(r, 30_000));
    try {
      await run("verify:verify", {
        address: addr,
        constructorArguments: [deployer.address, restricted],
      });
    } catch (e) {
      console.warn("Verification skipped:", e.message);
    }
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
