require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: "../../.env" });

const RPC_URL = process.env.ANCHOR_RPC_URL || "https://sepolia.base.org";
const DEPLOYER_KEY = process.env.ANCHOR_DEPLOYER_PRIVATE_KEY || "";
const CHAIN_ID = parseInt(process.env.ANCHOR_CHAIN_ID || "84532", 10);

/** @type {import('hardhat/config').HardhatUserConfig} */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true,
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  networks: {
    hardhat: {},
    baseSepolia: {
      url: RPC_URL,
      chainId: CHAIN_ID,
      accounts: DEPLOYER_KEY ? [DEPLOYER_KEY] : [],
    },
  },
  etherscan: {
    apiKey: {
      baseSepolia: process.env.BASESCAN_API_KEY || "",
    },
    customChains: [
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api-sepolia.basescan.org/api",
          browserURL: "https://sepolia.basescan.org",
        },
      },
    ],
  },
};
