export const loadRazorpayScript = () => {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }

    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

export const openRazorpayCheckout = (checkoutOptions) => {
  return new Promise((resolve, reject) => {
    if (!window.Razorpay) {
      reject(new Error("Razorpay SDK not loaded"));
      return;
    }

    const paymentWindow = new window.Razorpay({
      ...checkoutOptions,
      handler: (response) => resolve(response),
    });

    paymentWindow.on("payment.failed", (error) => {
      reject(new Error(error?.error?.description || "Payment failed"));
    });

    paymentWindow.open();
  });
};
