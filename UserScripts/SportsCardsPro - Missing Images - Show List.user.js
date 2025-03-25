// ==UserScript==
// @name         SportsCardsPro - Missing Images - Show List
// @namespace    http://tampermonkey.net/
// @version      1.2
// @author       jessedp <jessedp@gmail.com>
// @description  Add a 'Filter Missing Images' button and check for loading completion
// @match        https://www.sportscardspro.com/offers?*status=collection*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  // Create the 'Show Missing Images' dropdown
  const buttonWrapper = document.createElement("span");
  buttonWrapper.className = "tab settings dropdown";
  buttonWrapper.style.background = "forestgreen";

  // Create the main button
  const button = document.createElement("a");
  button.textContent = "Show Missing Images";
  button.href = "#";
  button.style.color = "white";
  buttonWrapper.appendChild(button);

  // Create the dropdown menu
  const dropdownMenu = document.createElement("div");
  dropdownMenu.className = "dropdown-menu";
  dropdownMenu.style.display = "none";
  dropdownMenu.style.position = "absolute";
  dropdownMenu.style.background = "white";
  dropdownMenu.style.border = "1px solid #ccc";
  dropdownMenu.style.zIndex = "1000";

  // Create the "Visible" option
  const visibleOption = document.createElement("a");
  visibleOption.textContent = "Visible";
  visibleOption.href = "#";
  visibleOption.style.display = "block";
  visibleOption.style.padding = "5px 10px";
  visibleOption.style.color = "black";
  visibleOption.addEventListener("click", (e) => {
    e.preventDefault();
    showVisible();
  });
  dropdownMenu.appendChild(visibleOption);

  // Create the "All" option
  const allOption = document.createElement("a");
  allOption.textContent = "All";
  allOption.href = "#";
  allOption.style.display = "block";
  allOption.style.padding = "5px 10px";
  allOption.style.color = "black";
  allOption.addEventListener("click", (e) => {
    e.preventDefault();
    showAll();
  });
  dropdownMenu.appendChild(allOption);

  buttonWrapper.appendChild(dropdownMenu);

  // Show dropdown on hover
  buttonWrapper.addEventListener("mouseenter", () => {
    dropdownMenu.style.display = "block";
  });

  buttonWrapper.addEventListener("mouseleave", () => {
    dropdownMenu.style.display = "none";
  });

  // Find the Settings tab and insert the new dropdown after it
  const settingsTab = document.querySelector("span.tab.settings");
  if (settingsTab) {
    settingsTab.insertAdjacentElement("afterend", buttonWrapper);
  } else {
    console.warn("Settings tab not found");
  }

  function showVisible() {
    const moreResultsButton = Array.from(
      document.querySelectorAll('input[type="submit"]')
    ).find((el) => el.value.includes("more results"));
    moreResultsButton.parentNode.remove();
    filterRows();
  }

  function showAll() {
    const scrollAndCheck = () => {
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });

      const checkForButton = setInterval(() => {
        const moreResultsButton = Array.from(
          document.querySelectorAll('input[type="submit"]')
        ).find((el) => el.value.includes("more results"));

        if (!moreResultsButton) {
          clearInterval(checkForButton);
          console.log("finished loading, looking...");
          filterRows();
        } else {
          window.scrollTo({
            top: document.body.scrollHeight,
            behavior: "smooth",
          });
        }
      }, 200);
    };

    scrollAndCheck();
  }

  function filterRows() {
    document.querySelectorAll("tr.offer").forEach(function (row) {
      row.style.display = "none";
    });
    document.querySelectorAll("tr.offer").forEach(function (row) {
      if (
        row.querySelector(
          'img[src="https://www.pricecharting.com/images/no-image-available.png"]'
        )
      ) {
        row.style.display = "";
      } else {
        var nextRow = row.nextElementSibling;
        if (nextRow && nextRow.classList.contains("gap")) {
          nextRow.style.display = "none";
        }
      }
    });
  }
})();
