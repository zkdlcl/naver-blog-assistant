const passwordInput = document.querySelector("#passwordInput");
const loginButton = document.querySelector("#loginButton");
const loginStatus = document.querySelector("#loginStatus");

async function login() {
  const password = passwordInput.value;
  loginButton.disabled = true;
  loginStatus.textContent = "";

  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      loginStatus.textContent = "비밀번호가 맞지 않습니다.";
      return;
    }

    window.location.href = "/";
  } catch {
    loginStatus.textContent = "로그인 요청에 실패했습니다.";
  } finally {
    loginButton.disabled = false;
  }
}

loginButton.addEventListener("click", login);
passwordInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    login();
  }
});
