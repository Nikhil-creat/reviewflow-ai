export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const WS_URL = (process.env.NEXT_PUBLIC_WS_URL || API_URL.replace(/^http/, "ws")).replace(/\/$/, "");
export const CREDIT = {
  name: "NIKHIL CHARY SRIRAMOJU",
  github: "https://github.com/Nikhil-creat",
  linkedin: "https://in.linkedin.com/in/nikhil-chary-sriramoju-95041b38a",
  email: "sriramojunikhil66@gmail.com",
};
