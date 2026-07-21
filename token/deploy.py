"""
نشر BAK-Coin على BSC Testnet
=============================
الخطوات:
1. ثبّت Hardhat: npm install --save-dev hardhat
2. ثبّت OpenZeppelin: npm install @openzeppelin/contracts
3. نشر: npx hardhat run scripts/deploy.js --network bscTestnet

أو استخدم Remix:
1. افتح remix.org
2. ألصق الكود
3.Compile
4. Deploy to BSC Testnet (MetaMask)
"""

# للنشر على Testnet مباشرة
DEPLOY_INSTRUCTIONS = """
=== خطوات النشر على BSC Testnet ===

1. حمّل MetaMask من https://metamask.io
2. أضف BSC Testnet:
   - Network Name: BSC Testnet
   - RPC URL: https://data-seed-prebsc-1-s1.binance.org:8545/
   - Chain ID: 97
   - Symbol: TBNB
   - Explorer: https://testnet.bscscan.com

3. احصل على TBNB مجاني من:
   https://testnet.bscscan.com/faucet

4. افتح https://remix.org

5. أنشئ ملف BAKCoin.sol والصق الكود

6.Compile (الضغط على Compile)

7. Deploy:
   - Environment: Injected Provider - MetaMask
   - شبكتها: BSC Testnet
   - اضغط Deploy
   - وافق في MetaMask

8. النتيجة: توكن BAK على Testnet

=== للنشر على Mainnet ===
1. احصل على BNB (~$50)
2. كرر نفس الخطوات مع BSC Mainnet
3. أضف السيولة على PancakeSwap
"""
