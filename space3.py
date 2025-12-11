import requests
import json
import time
import random
import pandas as pd
from eth_account import Account
from eth_account.messages import encode_defunct
import getpass
from faker import Faker
import msoffcrypto
from io import BytesIO  # 确保导入 BytesIO
import urllib3
from requests.exceptions import ProxyError, Timeout, RequestException, ReadTimeout


import imaplib
import email
from email.header import decode_header
import webbrowser
import os
import re
from bs4 import BeautifulSoup
import traceback

import asyncio
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from rich.logging import RichHandler
import logging

fake = Faker()  # 创建一个 Faker 对象

# 配置重试次数和延迟时间（秒）
MAX_RETRIES = 2
RETRY_DELAY = 15  # 每次重试之间的延迟（秒）
CHECK_DELAY = random.uniform(30, 60)  # 随机延迟时间（60到180秒）

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

# 获取 logger
logger = logging.getLogger("rich")

# API 端点
CHECK_WALLET_URL = "https://api.spaceandtime.dev/cloud-router/gateway/walletid/"
USER_URL = "https://api.spaceandtime.dev/cloud-router/gateway/userid/"
REGISTER_URL = "https://api.spaceandtime.dev/v1/auth/wallet/code-register"
AUTH_URL = "https://api.spaceandtime.dev/v1/auth/token"
SQL_GEN_URL = "https://api.spaceandtime.dev/v1/ai/sql/generate"
SAVE_SQL_URL = "https://api.spaceandtime.dev/v2/content/queries"
SQL_QUERY_URL = "https://api.spaceandtime.dev/v1/sql"
TOKEN_REFRESH_URL = "https://api.spaceandtime.dev/v1/auth/token/refresh"

# 读取 Excel 文件
EXCEL_FILE = 'wallets3.xlsx'
POXY_FILE = 'proxy_list.txt'

EXCEL_PASSWORD = getpass.getpass("请输入 Excel 文件密码: ")

# 预定义 SQL 查询模板
SQL_PROMPTS = [
    "Get the number of blocks created on Bitcoin per day over the last month.",
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?",
    "Show me the 10 largest transactions on ZKsync in the past 24 hours.",
    "What is the total transaction volume on Polygon for the last 7 days?",
    "Retrieve the number of active wallet addresses on Sui in the past 30 days.",
    "What are the top 10 Aptos accounts with the highest balance?",
    "Count the number of validators active on Ethereum Beacon today.",
    "How many blocks were produced on HOLESKY in the last week?",
    "Retrieve the average transaction fee on Sepolia over the past month.",
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days.",
    "Get the number of failed transactions on Bitcoin in the last 24 hours.",
    "What was the total gas used on ZKsync in the past 30 days?",
    "Find the top 10 liquidity pools on Polygon by total value locked.",
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week.",
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?",
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days.",
    "Find the largest transaction on HOLESKY in the last 12 hours.",
    "Show the number of new wallet addresses created on Sepolia last month.",
    "What is the total supply of USDC on Ethereum as of today?",
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days.",
    "List the top 10 bridges used on ZKsync in the past 3 months.",
    "How many DEX swaps occurred on Polygon last week?",
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours.",
    "Count the number of DeFi transactions on Aptos in the last 6 months.",
    "Retrieve the total staked ETH amount on Ethereum Beacon today.",
    "Get the total number of transactions processed on HOLESKY in the past month.",
    "What is the daily average block time on Sepolia in the last 30 days?",
    "List the 10 most frequently interacted smart contracts on Bitcoin.",
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week.",
    "Show the number of NFT minting transactions on ZKsync in the last 14 days.",
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month.",
    "Retrieve the number of lending protocol interactions on Sui in the last week.",
    "How many governance proposals were created on Aptos in the past 90 days?",
    "Show the validator with the highest uptime on Ethereum Beacon today.",
    "Find the largest whale transaction on HOLESKY in the last 48 hours.",
    "Get the number of token swaps executed on Sepolia in the past month.",
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days.",
    "What is the total gas burned on Bitcoin in the past 3 months?",
    "Count the number of multi-signature wallet transactions on ZKsync last week.",
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month.",
    "Show the number of oracle updates recorded on Sui in the past 6 months.",
    "Get the number of token holders of APT (Aptos) today.",
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits.",
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?",
    "Find the average gas fee for executing smart contracts on Sepolia last month.",
    "Show the most active NFT traders on Bitcoin in the past 30 days.",
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync.",
    "How many flash loan transactions were executed on Polygon last week?",
    "Show the number of contract interactions on Sui in the past month.",
    "Get the number of new blocks mined on Bitcoin in the last 24 hours.",
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?",
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days.",
    "What is the total gas spent on transactions on Polygon in the last 14 days?",
    "Retrieve the number of active validator nodes on Solana in the past 30 days.",
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?",
    "How many blocks have been generated on Ethereum Classic in the past month?",
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days.",
    "Show the top 5 NFT collections with the most trades on Flow in the past week.",
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours.",
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?",
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week.",
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days.",
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?",
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days.",
    "Find the largest transaction on Optimism in the last 12 hours.",
    "Show the number of newly created wallet addresses on Ethereum Classic last month.",
    "What is the total supply of DAI on Ethereum as of today?",
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days.",
    "List the top 5 most used bridges on Polkadot in the past 3 months.",
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?",
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours.",
    "Get the total number of transactions processed on StarkNet in the past month.",
    "What is the daily average block production rate on Terra in the last 30 days?",
    "List the 10 most frequently interacted smart contracts on Solana.",
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week.",
    "Show the number of NFT minting transactions on Tezos in the last 14 days.",
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month.",
    "Retrieve the number of lending protocol interactions on Aave in the last week.",
    "How many governance proposals were submitted on Polkadot in the last 90 days?",
    "Show the validator with the highest uptime on Tezos today.",
    "Find the largest whale transaction on Solana in the last 48 hours.",
    "Get the number of token swaps executed on PancakeSwap in the past month.",
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days.",
    "What is the total gas burned on Ethereum in the last 3 months?",
    "Count the number of multi-signature wallet transactions on Avalanche last week.",
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month.",
    "Show the number of oracle updates recorded on Chainlink in the past 6 months.",
    "Get the number of token holders of SOL (Solana) today.",
    "Retrieve the top 5 staking pools on Tezos by total deposits.",
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?",
    "Find the average gas fee for executing smart contracts on Ethereum in the last month.",
    "Show the most active NFT traders on Solana in the past 30 days.",
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum.",
    "How many flash loan transactions were executed on Aave in the last week?",
    "Show the number of contract interactions on Avalanche in the past month.",
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?",    
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?",
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours.",
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days.",
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana.",
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of blocks created on Bitcoin per day over the last month."
    "How many smart contracts were deployed on Ethereum from January 1 through January 31, 2024?"
    "Show me the 10 largest transactions on ZKsync in the past 24 hours."
    "What is the total transaction volume on Polygon for the last 7 days?"
    "Retrieve the number of active wallet addresses on Sui in the past 30 days."
    "What are the top 10 Aptos accounts with the highest balance?"
    "Count the number of validators active on Ethereum Beacon today."
    "How many blocks were produced on HOLESKY in the last week?"
    "Retrieve the average transaction fee on Sepolia over the past month."
    "Show the top 5 NFT collections traded on Ethereum in the past 7 days."
    "Get the number of failed transactions on Bitcoin in the last 24 hours."
    "What was the total gas used on ZKsync in the past 30 days?"
    "Find the top 10 liquidity pools on Polygon by total value locked."
    "Retrieve the top 5 addresses with the most token transfers on Sui in the last week."
    "How many unique wallet addresses interacted with smart contracts on Aptos yesterday?"
    "Get the number of withdrawals processed on Ethereum Beacon in the past 30 days."
    "Find the largest transaction on HOLESKY in the last 12 hours."
    "Show the number of new wallet addresses created on Sepolia last month."
    "What is the total supply of USDC on Ethereum as of today?"
    "Retrieve the count of token approvals granted on Bitcoin in the last 7 days."
    "List the top 10 bridges used on ZKsync in the past 3 months."
    "How many DEX swaps occurred on Polygon last week?"
    "Show the 5 addresses that paid the highest gas fees on Sui in the last 24 hours."
    "Count the number of DeFi transactions on Aptos in the last 6 months."
    "Retrieve the total staked ETH amount on Ethereum Beacon today."
    "Get the total number of transactions processed on HOLESKY in the past month."
    "What is the daily average block time on Sepolia in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Bitcoin."
    "Get the total amount of wrapped Bitcoin (WBTC) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on ZKsync in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Polygon in the past month."
    "Retrieve the number of lending protocol interactions on Sui in the last week."
    "How many governance proposals were created on Aptos in the past 90 days?"
    "Show the validator with the highest uptime on Ethereum Beacon today."
    "Find the largest whale transaction on HOLESKY in the last 48 hours."
    "Get the number of token swaps executed on Sepolia in the past month."
    "Show the total trading volume on Uniswap v3 on Ethereum in the last 7 days."
    "What is the total gas burned on Bitcoin in the past 3 months?"
    "Count the number of multi-signature wallet transactions on ZKsync last week."
    "Retrieve the number of cross-chain swaps from Polygon to Ethereum over the last month."
    "Show the number of oracle updates recorded on Sui in the past 6 months."
    "Get the number of token holders of APT (Aptos) today."
    "Retrieve the top 5 staking pools on Ethereum Beacon by total deposits."
    "What is the number of successfully finalized blocks on HOLESKY in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Sepolia last month."
    "Show the most active NFT traders on Bitcoin in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on ZKsync."
    "How many flash loan transactions were executed on Polygon last week?"
    "Show the number of contract interactions on Sui in the past month."
    "Get the number of new blocks mined on Bitcoin in the last 24 hours."
    "How many ERC-20 tokens were transferred on Ethereum from February 1 through February 7, 2024?"
    "Show me the top 5 NFT projects with the most trades on ZKsync in the past 30 days."
    "What is the total gas spent on transactions on Polygon in the last 14 days?"
    "Retrieve the number of active validator nodes on Solana in the past 30 days."
    "What are the top 10 largest transactions on Avalanche in the past 24 hours?"
    "How many blocks have been generated on Ethereum Classic in the past month?"
    "Retrieve the average transaction fee for Bitcoin transactions over the past 7 days."
    "Show the top 5 NFT collections with the most trades on Flow in the past week."
    "Get the number of failed transactions on Binance Smart Chain in the last 48 hours."
    "What was the total gas used for all Ethereum transactions on Sepolia in the past 30 days?"
    "Find the top 5 liquidity pools on Uniswap v3 by TVL on Ethereum in the last week."
    "Retrieve the top 10 addresses with the most token transfers on Arbitrum in the past 30 days."
    "How many unique wallets interacted with DeFi protocols on Polygon yesterday?"
    "Get the number of successful withdrawals processed on Avalanche in the past 30 days."
    "Find the largest transaction on Optimism in the last 12 hours."
    "Show the number of newly created wallet addresses on Ethereum Classic last month."
    "What is the total supply of DAI on Ethereum as of today?"
    "Retrieve the count of ERC-1155 token approvals on ZKsync in the last 7 days."
    "List the top 5 most used bridges on Polkadot in the past 3 months."
    "How many decentralized exchange (DEX) swaps were executed on SushiSwap last week?"
    "Show the 5 addresses that paid the highest gas fees for Ethereum transactions in the last 24 hours."
    "Get the total number of transactions processed on StarkNet in the past month."
    "What is the daily average block production rate on Terra in the last 30 days?"
    "List the 10 most frequently interacted smart contracts on Solana."
    "Get the total amount of Wrapped Ether (WETH) transferred on Ethereum last week."
    "Show the number of NFT minting transactions on Tezos in the last 14 days."
    "Find the top 5 stablecoins by transaction volume on Binance Smart Chain in the past month."
    "Retrieve the number of lending protocol interactions on Aave in the last week."
    "How many governance proposals were submitted on Polkadot in the last 90 days?"
    "Show the validator with the highest uptime on Tezos today."
    "Find the largest whale transaction on Solana in the last 48 hours."
    "Get the number of token swaps executed on PancakeSwap in the past month."
    "Show the total trading volume on Uniswap v3 on Polygon in the last 7 days."
    "What is the total gas burned on Ethereum in the last 3 months?"
    "Count the number of multi-signature wallet transactions on Avalanche last week."
    "Retrieve the number of cross-chain swaps from Arbitrum to Ethereum over the last month."
    "Show the number of oracle updates recorded on Chainlink in the past 6 months."
    "Get the number of token holders of SOL (Solana) today."
    "Retrieve the top 5 staking pools on Tezos by total deposits."
    "What is the number of successfully finalized blocks on Binance Smart Chain in the last 24 hours?"
    "Find the average gas fee for executing smart contracts on Ethereum in the last month."
    "Show the most active NFT traders on Solana in the past 30 days."
    "Retrieve the number of transactions associated with decentralized identity protocols on Ethereum."
    "How many flash loan transactions were executed on Aave in the last week?"
    "Show the number of contract interactions on Avalanche in the past month."
    "What is the total amount of ETH transferred between EOAs on Binance Smart Chain in the last 3 days?"
    "What is the total ETH transferred between EOAs on Ethereum in the last 3 days?"
    "Get the number of active validators on ZKsync in the last 30 days."
    "Find the largest liquidity pool on Polygon by TVL."
    "Show the number of NFT minting transactions on Ethereum in the last 30 days.",
]

# 邮箱配置
IMAP_SERVER = 'imap.rambler.ru'
EMAIL_ACCOUNT = 'imtinvilitiapa2793@rambler.ru'
EMAIL_PASSWORD = ''  # 输入邮箱密码

# 激活链接的正则表达式
ACTIVATION_LINK_REGEX = r'(https?://[^\s]+)'

headers = {
    #"Authorization": f"Bearer {access_token}",  # 使用登录后获得的 accessToken
    "Accept": "application/json",                # 期待返回 JSON 格式的数据
    "Accept-Encoding": "gzip, deflate, br, zstd",  # 支持多种压缩格式
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,ru;q=0.6",          # 设置语言为中文
    "Content-Type": "application/json",          # 指定请求体为 JSON 格式
    "Origin": "https://app.spaceandtime.ai",      # 来源网站，通常需要与 referer 配对
    "Referer": "https://app.spaceandtime.ai/",    # 请求来源页面
    "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',  # 浏览器信息
    "Sec-CH-UA-Mobile": "?0",                    # 是否为移动设备
    "Sec-CH-UA-Platform": '"Windows"',           # 操作系统平台
    "Sec-Fetch-Dest": "empty",                   # 表示没有特定的目标
    "Sec-Fetch-Mode": "cors",                    # 跨域请求模式
    "Sec-Fetch-Site": "cross-site",              # 请求来源网站
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",  # 用户代理
}

# 关闭 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 读取代理列表
def read_proxy_list(file_path=POXY_FILE):
    with open(file_path, 'r') as file:
        proxies = [line.strip() for line in file.readlines()]
    return proxies

# 随机选择一个代理 IP
def get_random_proxy(proxies):
    return random.choice(proxies)

# 配置代理（确保格式正确）
def set_proxy():
    proxies = read_proxy_list()  # 读取代理 IP 列表
    proxy = get_random_proxy(proxies)  # 随机选择一个代理
    logger.info(f"Using proxy: {proxy}")

    # 确保代理格式正确
    return {
        'http': f'http://{proxy}',  # HTTP 代理
        'https': f'http://{proxy}'  # HTTPS 也使用 HTTP 代理
    }

# 初始化 session
def create_session(proxy=None):
    """创建带代理的 requests.Session()"""
    session = requests.Session()
    session.verify = False  # 关闭 SSL 验证，排查 SSL 代理问题
    if proxy:
        session.proxies.update(proxy)  # 设置代理
    return session

# 通用请求方法，支持自动切换代理
def make_request(session, method, url, headers=None, json_data=None, params=None, proxy=None, retries=MAX_RETRIES, timeout=10):
    """通用请求方法，遇到代理失败自动切换"""
    while retries > 0:
        try:
            response = session.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,  # 添加 params 参数
                timeout=timeout,  # 设置超时时间
                proxies=proxy,
                verify=False  # 关闭 SSL 验证，排查 SSL 代理问题
            )
            if response.status_code in [200, 201]:
                return response
            else:
                logger.error(f"请求失败: {url}，状态码: {response.status_code}，响应: {response.text}")
                return response
        except (ProxyError, Timeout, ReadTimeout) as e:
            logger.warning(f"代理连接失败或超时，错误: {str(e)}，切换代理...")
            proxy = set_proxy()
            session.proxies.update(proxy)
        except RequestException as e:
            logger.error(f"请求异常: {str(e)}")
        retries -= 1
        time.sleep(2)  # 休眠 2 秒后重试

    logger.error("⚠️ 超过最大重试次数，跳过该请求")
    return None

# 检查钱包地址是否已注册
def check_wallet_registered(session, wallet_addr, proxy):
    logger.info(f"Checking if wallet address {wallet_addr} is registered...")
    response = make_request(session, "GET", f"{CHECK_WALLET_URL}{wallet_addr}", headers=headers, proxy=proxy)
    if response and response.status_code == 200:
        is_exist = response.json().get("code", {}).get("is_exist", False)
        logger.info(f"Wallet address {wallet_addr} registered: {is_exist}")
        return is_exist
    else:
        logger.warning(f"Wallet address {wallet_addr} is not registered yet. Response: {response.text}")
    return False

# 检查userid是否已注册
def check_user_registered(session, userid, proxy):
    logger.info(f"Checking if userid {userid} is registered...")
    response = make_request(session, "GET", f"{USER_URL}{userid}", headers=headers, proxy=proxy)
    if response and response.status_code == 200:
        is_exist = response.json().get("code", {}).get("is_exist", False)
        logger.info(f"Userid {userid} registered: {is_exist}")
        return is_exist
    else:
        logger.error(f"Userid {userid} is not registered yet.")
    return False

# 注册用户
def register_user(session, user, proxy):
    logger.info(f"Registering user {user['userId']} with wallet address {user['walletAddr']}")
    # 清理 userId 和 email 字段，确保没有多余空格或特殊字符
    user_id = user["userId"].strip()
    email = user["email"].strip()
    headers1 = {"Accept": "application/json"}
    
    payload = {
        "userId": user_id,
        "prefix": "Hi there from Space and Time Studio dApp! Sign this message to prove you have access to this wallet and we'll log you in. This is free- it won't cost you any Ether.\n  To stop hackers using your wallet, here's a unique auth code they can't guess: ",
        "joinCode": "",
        "walletAddr": user["walletAddr"].lower(),
        "email": email
    }
    logger.info(f"User {user['userId']} register payload: {payload}")
    response = make_request(session, "POST", REGISTER_URL, json_data=payload, headers=headers1, proxy=proxy)
    if response and response.status_code == 200:
        auth_code = response.json().get("authCode")
        logger.info(f"User {user['userId']} registered successfully. Auth code: {auth_code}. Response text: {response.text}")
        return auth_code
    else:
        logger.error(f"Failed to register user {user['userId']}. ")
    return None

# 获取 authCode 进行登录
def get_auth_code(session, user, proxy):
    logger.info(f"Getting auth code for address {user['walletAddr']}")
    payload = {
        "userId": None,
        "prefix": "Hi there from Space and Time Studio dApp! Sign this message to prove you have access to this wallet and we'll log you in. This is free- it won't cost you any Ether.\n  To stop hackers using your wallet, here's a unique auth code they can't guess: ",
        "joinCode": None,
        "walletAddr": user["walletAddr"].lower()
    }
    #headers = {"Accept": "application/json"}
    response = make_request(session, "POST", REGISTER_URL.replace("code-register", "code"), json_data=payload, headers=headers, proxy=proxy)
    if response and response.status_code == 200:
        auth_code = response.json().get("authCode", None)
        user_id =  response.json().get("userId", None)
        logger.info(f"Auth code received: {auth_code} for user: {user_id}")
        return auth_code, user_id
    else:
        logger.error(f"Failed to get auth code. ")
    return None, None

# 使用 authCode 进行签名
def sign_auth_code(auth_code, private_key):
    logger.info(f"Signing auth code with private key.")
    sign_text= f"Hi there from Space and Time Studio dApp! Sign this message to prove you have access to this wallet and we'll log you in. This is free- it won't cost you any Ether.\n  To stop hackers using your wallet, here's a unique auth code they can't guess: {auth_code}"
    message = encode_defunct(text=sign_text)
    logger.info(f"Message to sign: {sign_text}...")  # Log first 10 chars for security
    signed_message = Account.sign_message(message, private_key)
    logger.info(f"Signed message: {signed_message.signature.hex()[:10]}...")  # Log first 10 chars for security
    return '0x' + signed_message.signature.hex()

# 登录获取 accessToken
def login_user(session, user, auth_code, signature, proxy):
    logger.info(f"Logging in user {user['userId']} with auth code and signature.")
    payload = {
        "userId": user["userId"],
        "authCode": auth_code,
        "signature": signature,
        "key": user["walletAddr"].lower(),
        "scheme": "eth"
    }
    response = make_request(session, "POST", AUTH_URL, json_data=payload, headers=headers, proxy=proxy)
    if response and response.status_code == 200:
        access_token = response.json().get("accessToken")
        refresh_token = response.json().get("refreshToken")
        logger.info(f"User {user['userId']} logged in successfully. Access Token: {access_token[:10]}...")
        return access_token, refresh_token
    else:
        logger.error(f"Failed to log in user {user['userId']}. ")
    return None, None

# 刷新 Access Token
def refresh_token(session, refresh_token, proxy):
    logger.info("Refreshing token...")
    payload = {"refreshToken": refresh_token}
    #headers = {"Accept": "application/json"}
    response = make_request(session, "POST", TOKEN_REFRESH_URL, json_data=payload, headers=headers, proxy=proxy)
    
    if response and response.status_code == 200:
        data = response.json()
        access_token = data.get("accessToken")
        refresh_token = data.get("refreshToken")
        logger.info(f"Token refreshed successfully. Access Token: {access_token[:10]}...")  # Log first 10 chars for security
        return access_token, refresh_token
    else:
        logger.error(f"Failed to refresh token. ")
    return None, None

# 生成 SQL 查询
def generate_sql(session, access_token, proxy, user_id):
    logger.info("Generating SQL queries...")
    sql_queries = []
    sql_num = random.randint(1, 5)
    selected_prompts = random.sample(SQL_PROMPTS, sql_num)  # 随机选择 1 到 5 条
    for prompt in selected_prompts:
        payload = {"prompt": prompt, "metadata": {}}
        headers1 = {
            "Authorization": f"Bearer {access_token}",  # 使用登录后获得的 accessToken
            "Accept": "application/json",                # 期待返回 JSON 格式的数据
            "Accept-Encoding": "gzip, deflate, br, zstd",  # 支持多种压缩格式
            "Accept-Language": "zh-CN,zh;q=0.9",          # 设置语言为中文
            "Content-Type": "application/json",          # 指定请求体为 JSON 格式
            "Origin": "https://app.spaceandtime.ai",      # 来源网站，通常需要与 referer 配对
            "Referer": "https://app.spaceandtime.ai/",    # 请求来源页面
            "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',  # 浏览器信息
            "Sec-CH-UA-Mobile": "?0",                    # 是否为移动设备
            "Sec-CH-UA-Platform": '"Windows"',           # 操作系统平台
            "Sec-Fetch-Dest": "empty",                   # 表示没有特定的目标
            "Sec-Fetch-Mode": "cors",                    # 跨域请求模式
            "Sec-Fetch-Site": "cross-site",              # 请求来源网站
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",  # 用户代理
        }
        response = make_request(session, "POST", SQL_GEN_URL, json_data=payload, headers=headers1, proxy=proxy)
        
        if response and response.status_code in [200, 201]:
            sql_query = response.json().get("SQL")
            sql_queries.append((sql_query, prompt))  # 保存 SQL 查询和对应的 prompt
        elif not response or response.status_code == 402:  # 处理 response 为 None 或 402 的情况
            logger.warning("⚠️ Trial expired or request failed. Fetching random SQL queries from local Excel.")
            random_queries = get_random_sql_from_excel(user_id, sql_num)
            if random_queries:
                for query in random_queries:
                    sql_queries.append((query["queryText"], query["description"]))
                break  # 如果从本地获取到 SQL 查询，直接跳出循环
            else:
                logger.error("⚠️ No local SQL queries found in Excel file.")
        else:
            logger.error(f"Failed to generate SQL query for prompt: {prompt}. Status code: {response.status_code if response else '无响应'}")

    logger.info(f"Generated {len(sql_queries)} SQL queries successfully")
    return sql_queries

# 新增查询 SQL 方法
def query_sql(session, access_token, sql_text, proxy):
    """执行 SQL 查询并返回结果，出现异常时不会中断程序"""
    logger.info(f"Executing SQL query: {sql_text}")
    try:
        # 构建 SQL 查询的 payload
        payload = {
            "sqlText": sql_text,
            "validate": True
        }
        headers1 = {
            "Authorization": f"Bearer {access_token}",  # 使用登录后获得的 accessToken
            "Accept": "application/json",                # 期待返回 JSON 格式的数据
            "Accept-Encoding": "gzip, deflate, br, zstd",  # 支持多种压缩格式
            "Accept-Language": "zh-CN,zh;q=0.9",          # 设置语言为中文
            "Content-Type": "application/json",          # 指定请求体为 JSON 格式
            "Origin": "https://app.spaceandtime.ai",      # 来源网站，通常需要与 referer 配对
            "Referer": "https://app.spaceandtime.ai/",    # 请求来源页面
            "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',  # 浏览器信息
            "Sec-CH-UA-Mobile": "?0",                    # 是否为移动设备
            "Sec-CH-UA-Platform": '"Windows"',           # 操作系统平台
            "Sec-Fetch-Dest": "empty",                   # 表示没有特定的目标
            "Sec-Fetch-Mode": "cors",                    # 跨域请求模式
            "Sec-Fetch-Site": "cross-site",              # 请求来源网站
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",  # 用户代理
        }
        # 发送 SQL 查询请求
        response = make_request(session, "POST", SQL_QUERY_URL, json_data=payload, headers=headers1, proxy=proxy)
        
        if response and response.status_code in [200, 201]:
            # 成功时返回查询结果
            return response  # 解析返回的 JSON 数据
        else:
            logger.error(f"Failed to execute SQL query. ")
    except Exception as e:
        logger.error(f"Error occurred while executing SQL query: {e}")
    return None


# 保存 SQL 查询
def save_sql(session, access_token, sql_queries, proxy):
    logger.info(f"Start to save SQL query...")
    bool_return = True
    for sql_query, prompt in sql_queries:
        # 提取不超过 50 个字符的名称
        name_length = random.randint(30, 50)
        name = prompt[:name_length]  # 截取前 30 个字符作为名称
        description = prompt  # 使用完整的 prompt 作为描述

        # 执行 SQL 查询获取结果
        response = query_sql(session, access_token, sql_query, proxy)
        if response and response.status_code in [200, 201]:
            # 如果查询成功，打印查询结果
            logger.info(f"SQL query result: {response.text}")
            
        logger.info(f"Saving SQL query:\n{sql_query}")
        payload = {
            "name": name,
            "description": description,
            "queryText": sql_query,
            "newTags": [],
            "tagReferences": []
        }
        headers1 = {
            "Authorization": f"Bearer {access_token}",  # 使用登录后获得的 accessToken
            "Accept": "application/json",                # 期待返回 JSON 格式的数据
            "Accept-Encoding": "gzip, deflate, br, zstd",  # 支持多种压缩格式
            "Accept-Language": "zh-CN,zh;q=0.9",          # 设置语言为中文
            "Content-Type": "application/json",          # 指定请求体为 JSON 格式
            "Origin": "https://app.spaceandtime.ai",      # 来源网站，通常需要与 referer 配对
            "Referer": "https://app.spaceandtime.ai/",    # 请求来源页面
            "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',  # 浏览器信息
            "Sec-CH-UA-Mobile": "?0",                    # 是否为移动设备
            "Sec-CH-UA-Platform": '"Windows"',           # 操作系统平台
            "Sec-Fetch-Dest": "empty",                   # 表示没有特定的目标
            "Sec-Fetch-Mode": "cors",                    # 跨域请求模式
            "Sec-Fetch-Site": "cross-site",              # 请求来源网站
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",  # 用户代理
        }
        response = make_request(session, "POST", SAVE_SQL_URL, json_data=payload, headers=headers1, proxy=proxy)
        
        if response and response.status_code in [200, 201]:
            logger.info(f"SQL query saved response: {response.text}.")
            sleep_interver = random.randint(30, 60)
            logger.info(f"SQL query saved successfully with name: {name} and sleep {sleep_interver} seconds.")
            time.sleep(sleep_interver) 
        else:
            logger.error(f"Failed to save SQL query. ")
            bool_return = False
            continue
    return bool_return

def get_user_saved_sql(session, access_token, proxy):
    """获取用户保存的 SQL 查询"""
    url = "https://api.spaceandtime.dev/v2/content/queries"
    params = {
        "pageNo": 1,
        "pageSize": 50,
        "scope": "private",
        "sortBy": "modified",
        "sortOrder": "DESC"
    }
    headers1 = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://app.spaceandtime.ai",
        "Referer": "https://app.spaceandtime.ai/",
        "Sec-CH-UA": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    }
    response = make_request(session, "GET", url, headers=headers1, params=params, proxy=proxy)
    if response and response.status_code == 200:
        return response.json().get("content", [])
    else:
        logger.error(f"Failed to get user saved SQL queries. Status code: {response.status_code if response else '无响应'}")
        return []

def save_sql_to_excel(sql_queries, excel_file="saved_sql.xlsx"):
    """将 SQL 查询保存到本地 Excel 文件，并确保去重"""
    try:
        # 读取现有的 Excel 文件（如果存在）
        existing_queries = []
        try:
            df = pd.read_excel(excel_file)
            existing_queries = df["queryText"].tolist()
        except FileNotFoundError:
            pass  # 如果文件不存在，忽略

        # 将新的 SQL 查询添加到现有数据中
        new_queries = []
        for query in sql_queries:
            if query["queryText"] not in existing_queries:
                new_queries.append({
                    "userId": query["userId"],
                    "name": query["name"],
                    "description": query["description"],
                    "queryText": query["queryText"]
                })
                existing_queries.append(query["queryText"])

        # 如果有新的查询，保存到 Excel 文件
        if new_queries:
            new_df = pd.DataFrame(new_queries)
            # 如果文件存在，追加数据；否则创建新文件
            try:
                existing_df = pd.read_excel(excel_file)
                updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            except FileNotFoundError:
                updated_df = new_df

            # 保存到 Excel 文件
            updated_df.to_excel(excel_file, index=False)
            logger.info(f"✅ SQL query saved to Excel: {excel_file}")
    except Exception as e:
        logger.error(f"⚠️ Error saving SQL queries to Excel: {e}")

def get_random_sql_from_excel(user_id, sql_num):
    """从本地 Excel 文件中随机选择 1-3 条 SQL 查询，并确保是当前用户的查询"""
    try:
        excel_file="saved_sql.xlsx"
        df = pd.read_excel(excel_file)
        # 排除当前用户的 SQL 查询
        user_queries = df[df["userId"] != user_id].to_dict("records")
        
        if user_queries:
            return random.sample(user_queries, min(sql_num, len(user_queries)))
        else:
            logger.warning(f"⚠️ No SQL other's queries found in Excel file.")
            return []
    except FileNotFoundError:
        logger.error("⚠️ Excel file not found.")
        return []


def check_email_verified(session, access_token, proxy):
    """检查邮箱是否已验证"""
    url = "https://api.spaceandtime.dev/v1/user/email"
    headers1 = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://app.spaceandtime.ai",
        "Referer": "https://app.spaceandtime.ai/",
        "Sec-CH-UA": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    }
    response = make_request(session, "GET", url, headers=headers1, proxy=proxy)
    if response and response.status_code == 200:
        email_verified = response.json().get("emailVerified", False)
        logger.info(f"📩 Email verification status: {email_verified}")
        return email_verified
    else:
        logger.error(f"⚠️ Failed to check email verification. Response: {response.text}")
        return None

# 读取 Excel 文件
def read_users_from_excel(EXCEL_FILE):
    logger.info(f"Reading users from Excel file: {EXCEL_FILE}")
    try:
        with open(EXCEL_FILE, "rb") as f:
            office_file = msoffcrypto.OfficeFile(f)
            office_file.load_key(password=EXCEL_PASSWORD)  # 设置密码

            # 解密文件并存储在内存中
            decrypted_file = BytesIO()
            office_file.decrypt(decrypted_file)

            # 重设文件指针到文件开头
            decrypted_file.seek(0)

            # 使用 pandas 读取解密后的 Excel 文件，跳过第一行
            df = pd.read_excel(decrypted_file, skiprows=1)
            logger.info(f"Successfully read Excel file. Rows: {len(df)}")

            users = []
            for index, row in df.iterrows():
                email = row.iloc[0]  # 假设 email 是第一列
                wallet_addr = row.iloc[1]  # 假设 wallet address 是第二列
                private_key = row.iloc[2]  # 假设 private key 是第三列
                
                # 随机生成用户 ID
                user_id = fake.user_name() + str(random.randint(1000, 9999))

                # 将用户信息存入字典并添加到 users 列表
                users.append({"userId": user_id, "walletAddr": wallet_addr, "email": email, "privateKey": private_key})

            logger.info(f"Successfully extracted {len(users)} users from the Excel file.")
            return users
    except Exception as e:
        logger.error(f"Error occurred while reading Excel file: {e}")
        traceback.print_exc()

# 登录邮箱
def login_to_email():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    return mail

def resend_verification_email(session, access_token, proxy):
    """重新发送激活邮件"""
    url = "https://api.spaceandtime.dev/v1/auth/email/verify-resend"
    headers1 = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://app.spaceandtime.ai",
        "Referer": "https://app.spaceandtime.ai/",
        "Sec-CH-UA": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    }
    # 不需要传递 payload
    response = make_request(session, "POST", url, headers=headers1, proxy=proxy)
    if response and (response.status_code == 204 or response.status_code == 200):
        logger.info("📩 重新发送激活邮件成功")
        return True
    else:
        logger.error(f"⚠️ 重新发送激活邮件失败。状态码: {response.status_code if response else '无响应'}")
        return False

def check_and_activate_email(session, user, proxy, access_token):
    """检查邮箱并激活，激活成功后重新登录以获取新的 access_token"""
    mail = login_to_email()
    msg = get_verification_email(mail, user["email"])
    if msg:
        activation_link = extract_activation_link(msg)
        if activation_link:
            activation_link = clean_activation_link(activation_link)
            logger.info(f"Found activation link: {activation_link}")
            if activate_account_with_selenium(activation_link, proxy, access_token):
                logger.info(f"✅ 用户邮箱 {user['email']} 激活成功")
                
                # 激活成功后重新登录以获取新的 access_token
                auth_code, user_id = get_auth_code(session, user, proxy)
                if auth_code:
                    signature = sign_auth_code(auth_code, user["privateKey"])
                    new_access_token, new_refresh_token = login_user(session, user, auth_code, signature, proxy)
                    if new_access_token:
                        logger.info(f"✅ 重新登录成功，获取新的 access_token")
                        return new_access_token, new_refresh_token
                    else:
                        logger.error(f"❌ 重新登录失败")
                        return None, None
                else:
                    logger.error(f"❌ 获取新的 auth_code 失败")
                    return None, None
            else:
                logger.warning(f"⚠️ 用户邮箱 {user['email']} 激活失败")
                return None, None
        else:
            logger.warning(f"⚠️ 没找到激活链接：{user['email']}")
            return None, None
    else:
        logger.warning(f"⚠️ 没收到验证邮件：{user['email']}")
        return None, None

# 搜索并读取未读邮件，带重试机制
def get_verification_email(mail, to_email_address, retries=MAX_RETRIES):
    try:
        # 定义需要检查的文件夹
        folders_to_check = ['inbox', 'spam', 'trash', 'Spam', 'Trash']

        for folder in folders_to_check:
            # 选择邮件箱（如垃圾箱、垃圾邮件）
            status, response = mail.select(folder)
            
            # 检查是否成功选择文件夹
            if status != 'OK':
                logger.error(f"Failed to select folder {folder}")
                continue  # 如果当前文件夹无法选择，则继续检查下一个文件夹

            # 使用收件地址进行筛选：通过 TO 筛选指定邮箱的邮件
            status, messages = mail.search(None, f'(TO "{to_email_address}")')

            if status != 'OK' or not messages[0]:
                logger.info(f"No messages found in {folder} for {to_email_address}")
                continue  # 如果当前文件夹没有找到邮件，则继续检查下一个文件夹

            # 获取邮件ID
            email_ids = messages[0].split()

            for email_id in email_ids:
                # 获取邮件数据
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue  # 跳过获取失败的邮件

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # 解码邮件主题
                        subject, encoding = decode_header(msg['Subject'])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or 'utf-8')

                        logger.info(f"Checking email in {folder} with subject: {subject}")

                        # 检查邮件是否为验证邮件
                        if 'Please Verify Your Email' in subject:
                            logger.info(f"Found verification email in {folder} with subject: {subject}")
                            return msg

        # 如果没有找到有效邮件，抛出异常
        raise Exception("Verification email not found in any folder")

    except Exception as e:
        logger.error(f"Error: {e}")
        if retries > 0:
            logger.info(f"Retrying... ({MAX_RETRIES - retries + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)  # 等待一段时间后重试
            return get_verification_email(mail, to_email_address, retries-1)
        else:
            logger.warning("Max retries reached. Could not find verification email.")
            return None

# 提取激活链接
def extract_activation_link(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # 查找邮件中的激活链接
            if content_type == "text/plain" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode()
                # 假设激活链接是以 "http" 开头的链接
                activation_link = body.split("http")[1].strip().split()[0]
                return "http" + activation_link
    else:
        # 处理非 multipart 邮件
        body = msg.get_payload(decode=True).decode()
        # 假设激活链接是以 "http" 开头的链接
        activation_link = body.split("http")[1].strip().split()[0]
        return "http" + activation_link

    return None

# 清理激活链接中的特殊字符
def clean_activation_link(link):
    # URL 解码，去除可能的编码问题
    cleaned_link = urllib.parse.unquote(link)
    # 去掉链接末尾的多余 " 或其他不必要的字符
    if cleaned_link.endswith('"'):
        cleaned_link = cleaned_link[:-1]  # 去除末尾的引号
    return cleaned_link

# 激活账号
def activate_account(session, access_token, link, proxy, retries=3, delay=5):
    """
    尝试激活账户，最多重试 retries 次，每次失败后延迟 delay 秒。
    :param session: 请求会话对象
    :param access_token: 用户的 access token
    :param link: 激活链接
    :param proxy: 使用的代理
    :param retries: 最大重试次数
    :param delay: 每次重试之间的延迟时间（秒）
    :return: 成功返回 True，失败返回 False
    """
    headers1 = {
        #"Authorization": f"Bearer {access_token}",  # 使用登录后获得的 accessToken
        "Accept": "application/json",                # 期待返回 JSON 格式的数据
        "Accept-Encoding": "gzip, deflate, br, zstd",  # 支持多种压缩格式
        "Accept-Language": "zh-CN,zh;q=0.9",          # 设置语言为中文
        "Content-Type": "application/json",          # 指定请求体为 JSON 格式
        "Origin": "https://app.spaceandtime.ai",      # 来源网站，通常需要与 referer 配对
        "Referer": "https://app.spaceandtime.ai/",    # 请求来源页面
        "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',  # 浏览器信息
        "Sec-CH-UA-Mobile": "?0",                    # 是否为移动设备
        "Sec-CH-UA-Platform": '"Windows"',           # 操作系统平台
        "Sec-Fetch-Dest": "empty",                   # 表示没有特定的目标
        "Sec-Fetch-Mode": "cors",                    # 跨域请求模式
        "Sec-Fetch-Site": "cross-site",              # 请求来源网站
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",  # 用户代理
    }
    
    for attempt in range(retries):
        try:
            # 尝试发送请求
            logger.info(f"Attempt {attempt + 1}/{retries} to activate the account...")
            response = make_request(session, "POST", link, headers=headers1, allow_redirects=True, proxy=proxy, timeout=30)
            if response and response.status_code == 200:
                logger.info("✅ Account successfully activated!")
                return True
            elif response and response.status_code == 302:
                logger.info(f"Redirected to {response.headers['Location']}. Trying to follow the redirection.")
                response = make_request(session, "POST", response.headers['Location'], headers=headers, allow_redirects=True, proxy=proxy)
                if response.status_code == 200:
                    logger.info("Account successfully activated after following redirect!")
                    return True
                else:
                    logger.error(f"Failed to activate the account after redirection. Status Code: {response.status_code}")
            else:
                logger.error(f"❌ Failed to activate account. Retrying...")
        
        except requests.exceptions.RequestException as e:
            # 请求异常处理，记录异常并重试
            logger.error(f"Error during activation attempt: {e}. Retrying...")
        
        # 如果请求失败，等待一段时间后重试
        sleep_time = random.uniform(2, delay)  # 使用随机延迟
        logger.info(f"Waiting for {sleep_time:.2f} seconds before retrying...")
        time.sleep(sleep_time)

    # 如果超过最大重试次数仍未成功，输出错误
    logger.error("❌ Max retries reached. Could not activate the account.")
    return False

def activate_account_with_selenium(activation_link, proxy, access_token):
    # 创建 Chrome 配置
    chrome_options = webdriver.ChromeOptions()
    
    # 启用 Headless 模式
    chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速
    chrome_options.add_argument("--no-sandbox")  # 禁用沙盒模式
    chrome_options.add_argument("--disable-dev-shm-usage")  # 避免内存不足问题
    
    # 显式指定 Chrome 的路径
    chrome_options.binary_location = "/usr/bin/google-chrome"

    try:
        logger.info(f"Skipping activation link: {activation_link}")
        return False
        # 使用 Service 传入 chromedriver 路径
        # chromedriver_path = ChromeDriverManager().install()
        # service = Service(chromedriver_path)
        # driver = webdriver.Chrome(service=service, options=chrome_options)

        # 打开激活链接
        #driver.get(activation_link)
        # logger.info(f"Opening activation link: {activation_link}")
        
        # # 等待页面加载
        # time.sleep(15)

        # # 检查是否重定向到真正的激活链接
        # current_url = driver.current_url
        # if "verify-email" in current_url:
        #     # 提取真正的激活链接
        #     email_token = current_url.split("/")[-1]
        #     verify_url = f"https://api.spaceandtime.dev/v1/auth/email/verify?emailToken={email_token}"
            
        #     # 使用 requests 发送 POST 请求完成激活
        #     headers1 = {
        #         "Authorization": f"Bearer {access_token}",
        #         "Accept": "application/json",
        #         "Accept-Encoding": "gzip, deflate, br, zstd",
        #         "Accept-Language": "zh-CN,zh;q=0.9",
        #         "Content-Type": "application/json",
        #         "Origin": "https://app.spaceandtime.ai",
        #         "Referer": "https://app.spaceandtime.ai/",
        #         "Sec-CH-UA": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        #         "Sec-CH-UA-Mobile": "?0",
        #         "Sec-CH-UA-Platform": '"macOS"',
        #         "Sec-Fetch-Dest": "empty",
        #         "Sec-Fetch-Mode": "cors",
        #         "Sec-Fetch-Site": "cross-site",
        #         "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        #     }
        #     session = requests.Session()
        #     response = make_request(session, "POST", verify_url, headers=headers1, proxy=proxy)
            
        #     if response and (response.status_code == 204 or response.status_code == 200):
        #         logger.info("✅ 邮箱激活成功")
        #         return True
        #     else:
        #         logger.error(f"⚠️ 邮箱激活失败。状态码: {response.status_code if response else '无响应'}")
        #         return False
        # else:
        #     logger.error("⚠️ 未找到真正的激活链接")
        #     return False

    except Exception as e:
        logger.error(f"Error opening the activation link: {e}")
        return False

    finally:
        # 关闭浏览器
        if 'driver' in locals():
            driver.quit()


def save_progress(user_data):
    """每 10 条数据保存一次"""
    with open("user_data3.json", "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)
    logger.info(f"✅ 进度已保存，当前处理 {len(user_data)} 条数据")

def main():
    users = read_users_from_excel(EXCEL_FILE)
    random.shuffle(users)
    user_data = []
    
    for index, user in enumerate(users, 1):
        address = user["walletAddr"]
        email = user["email"]
        sql_queries = []  # 初始化 sql_queries 变量
        email_verified = False  # 初始化 email_verified 变量

        proxy = set_proxy()
        session = create_session(proxy)
        
        # 增加随机延迟，避免触发速率限制
        sleep_time = random.uniform(10, 30)  # 随机延迟 10 到 30 秒
        logger.info(f"⏳ 等待 {sleep_time:.2f} 秒，继续下一个用户...")
        time.sleep(sleep_time)

        bool_wallet_registered = check_wallet_registered(session, address.lower(), proxy)
        registration_status = "Registered" if bool_wallet_registered else "Not Registered"
        
        if bool_wallet_registered:
            auth_code, user_id = get_auth_code(session, user, proxy)
            user["userId"] = user_id
            signature = sign_auth_code(auth_code, user["privateKey"])
            access_token, refresh_token = login_user(session, user, auth_code, signature, proxy)
            
            if access_token:
                # 检查邮箱是否已激活
                email_verified = check_email_verified(session, access_token, proxy)
                if email_verified is False:
                    # 如果未激活，重新发送激活邮件
                    if resend_verification_email(session, access_token, proxy):
                        # 检查邮箱并激活，并获取新的 access_token
                        new_access_token, new_refresh_token = check_and_activate_email(session, user, proxy, access_token)
                        if new_access_token:
                            access_token = new_access_token
                            refresh_token = new_refresh_token
                else:
                    logger.info(f"📩 用户邮箱 {email} 已激活")
                
                # 获取用户保存的 SQL 查询
                saved_sql_queries = get_user_saved_sql(session, access_token, proxy)
                if saved_sql_queries:
                    # 将保存的 SQL 查询保存到 Excel 文件
                    save_sql_to_excel(saved_sql_queries)
                
                # 生成 SQL 查询
                sql_queries = generate_sql(session, access_token, proxy, user_id)
                if save_sql(session, access_token, sql_queries, proxy):
                    logger.info(f"✅ 用户 {user['userId']} 处理完成")
                else:
                    logger.error(f"❌ SQL 语句保存失败：{user['userId']}")
            else:
                logger.error(f"❌ 用户 {user['userId']} 登录失败")
        else:
            auth_code = register_user(session, user, proxy)
            if auth_code:
                signature = sign_auth_code(auth_code, user["privateKey"])
                access_token, refresh_token = login_user(session, user, auth_code, signature, proxy)
                if access_token:
                    # 检查邮箱并激活，并获取新的 access_token
                    new_access_token, new_refresh_token = check_and_activate_email(session, user, proxy, access_token)
                    if new_access_token:
                        access_token = new_access_token
                        refresh_token = new_refresh_token
                    
                    # 生成 SQL 查询
                    auth_code, user_id = get_auth_code(session, user, proxy)
                    sql_queries = generate_sql(session, access_token, proxy, user_id)
                    if save_sql(session, access_token, sql_queries, proxy):
                        logger.info(f"✅ 用户 {user['userId']} 处理完成")
                    else:
                        logger.error(f"❌ SQL 语句保存失败：{user['userId']}")
                else:
                    logger.error(f"❌ 用户 {user['userId']} 登录失败")
            else:
                logger.error(f"❌ 用户 {user['userId']} 注册失败")
        
        # 记录数据
        user_data.append({
            "userId": user["userId"],
            "walletAddr": user["walletAddr"],
            "email": user["email"],
            "registration_status": registration_status,
            "activation_status": "Activated" if email_verified else "Not Activated",
            "sql_queries": sql_queries  # 使用已定义的 sql_queries
        })
        
        # 每 10 条数据保存一次
        if index % 10 == 0:
            save_progress(user_data)
        sleep_interver = random.randint(600, 1200)
        logger.info(f"⏳ 等待 {sleep_interver} 秒，继续下一个用户...")
        time.sleep(sleep_interver)
        logger.info("--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
    
    # 处理完所有用户后，最终保存
    save_progress(user_data)
    logger.info("🎉 所有用户处理完成！")


# 执行主函数
if __name__ == "__main__":
    main()