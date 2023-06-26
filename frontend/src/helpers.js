export const BASE_URL = "";

export function random_bg_color() {
  // Get a random number between 64 to 256
  // (for getting lighter colors)
  let red = Math.floor(Math.random() * 256) + 70;
  let green = Math.floor(Math.random() * 256) + 70;
  let blue = Math.floor(Math.random() * 256) + 70;

  // Construct a color with the given values
  let bgColor = "rgb(" + red + ", " + green + ", " + blue + ")";

  // Set the background to the new color
  document.body.style.background = bgColor;
}

export function send_state_value(value) {
  fetch(`${BASE_URL}/state`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(value),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Success:", data);
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error:" + error);
    });
}
