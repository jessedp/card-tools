// ==UserScript==
// @name         SportsCardsPro - Missing Image - Create List
// @namespace    http://tampermonkey.net/
// @version      1.3
// @author       jessedp <jessedp@gmail.com>
// @description  Add a 'Missing Image List' button and check for loading completion
// @match        https://www.sportscardspro.com/offers?*status=collection*
// @grant        GM_openInTab
// ==/UserScript==

(function () {
  "use strict";

  // Create the 'Missing Image List' link
  const button = document.createElement("a");
  button.textContent = "Open Missing Image List";
  button.href = "#";
  button.style.color = "white";

  // Create a new span with the required class and add the link inside it
  const buttonWrapper = document.createElement("span");
  buttonWrapper.className = "tab settings";
  buttonWrapper.appendChild(button);
  buttonWrapper.style.background = "forestgreen";

  // Find the Settings tab and insert the new span after it
  const settingsTab = document.querySelector("span.tab.settings");
  if (settingsTab) {
    settingsTab.insertAdjacentElement("afterend", buttonWrapper);
  }

  button.addEventListener("click", () => {
    const scrollAndCheck = () => {
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });

      const checkForButton = setInterval(() => {
        const moreResultsButton = Array.from(
          document.querySelectorAll('input[type="submit"]')
        ).find((el) => el.value.includes("more results"));

        if (!moreResultsButton) {
          clearInterval(checkForButton);
          console.log("finished loading, looking...");
          findAndDisplay();
        } else {
          window.scrollTo({
            top: document.body.scrollHeight,
            behavior: "smooth",
          });
        }
      }, 200);
    };

    scrollAndCheck();
  });

  function findAndDisplay() {
    let titles = [];
    let rows = document.querySelectorAll("tr.offer");

    rows.forEach(function (row) {
      if (
        row.querySelector(
          'img[src="https://www.pricecharting.com/images/no-image-available.png"]'
        )
      ) {
        let titleElement = row.querySelector("p.title");
        if (titleElement) {
          let titleText = titleElement.innerHTML
            .replace(/<br\/?>/gi, " - ")
            .replace(/<[^>]*>/g, "")
            .trim()
            .replace(/\s+/g, " ")
            .trim();

          let parts = titleText.split(" - ");
          if (parts.length === 2) {
            titleText = parts[1] + " - " + parts[0];
          }

          titles.push(titleText);
        }
      }
    });

    window.scrollTo(0, 0);

    if (titles.length > 0) {
      let newWindow = window.open("", "");
      newWindow.document.write(
        "<title>" +
          titles.length +
          ' cards missing images</title><textarea style="width: 90%; height: 90%;">' +
          titles.join("\n") +
          "</textarea>"
      );
      newWindow.document.querySelector("textarea").select();
    } else {
      alert("No matching rows found.");
    }
  }
})();
