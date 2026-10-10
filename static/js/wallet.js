const SEPOLIA_CHAIN_ID = '0xaa36a7'; // Mã chuẩn của mạng Sepolia

async function connectWallet() {
    if (typeof window.ethereum === 'undefined') {
        alert("Vui lòng cài đặt tiện ích ví MetaMask trên trình duyệt!");
        return null;
    }

    try {
        // Yêu cầu người dùng kết nối ví
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        
        if (chainId !== SEPOLIA_CHAIN_ID) {
            alert("Sai mạng lưới! Vui lòng mở MetaMask và chuyển sang mạng Sepolia Testnet.");
            return null;
        }
        return accounts[0]; // Trả về địa chỉ ví
    } catch (error) {
        console.error("Lỗi kết nối:", error);
        alert("Không thể kết nối ví: " + error.message);
        return null;
    }
}

async function sendTransaction(account, toAddress, txData) {
    try {
        const txParams = {
            from: account,
            to: toAddress,
            data: txData, // Dữ liệu giao dịch (đã được Backend mã hóa sẵn)
        };
        
        // Gọi MetaMask bật lên yêu cầu Ký
        const txHash = await window.ethereum.request({
            method: 'eth_sendTransaction',
            params: [txParams],
        });
        
        return txHash;
    } catch (error) {
        console.error("Lỗi ký giao dịch:", error);
        alert("Giao dịch bị từ chối hoặc có lỗi xảy ra.");
        return null;
    }
}