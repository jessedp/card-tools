// ==UserScript==
// @name         SportscardsPro - Site Wide - History Overlay CSS overrides
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Track and display the last five pages visited on SportscardsPro
// @author       Your Name
// @match        https://www.sportscardspro.com/*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  // Exit if the script is running inside an iframe
  if (window !== window.top) return;

  const STORAGE_KEY = "lastFivePages";

  // Function to update the last five pages in localStorage
  function updatePageHistory() {
    // Remove base URL and query parameters
    const currentPage = window.location.href;

    let pages = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];

    // Avoid duplicate entries for the same page
    if (
      currentPage.includes("/offer") ||
      (currentPage.includes("/publish-offer") &&
        currentPage.includes("add-to-collection=1")) ||
      currentPage.includes("/end-offer") ||
      pages.includes(currentPage)
    )
      return;

    console.log(`${pages[0]} !== ${currentPage}`);
    if (pages[0] !== currentPage) {
      pages.unshift(currentPage);
    }

    // Keep only the last 5 entries
    if (pages.length > 5) {
      pages = pages.slice(0, 5);
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(pages));
  }

  // Function to create the page history list
  function displayPageHistory() {
    const logoutLink = document.querySelector(
      'a[href^="https://www.sportscardspro.com/logout"]'
    );
    if (!logoutLink) return;

    let pages = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];

    // Create or update the list
    let listContainer = document.getElementById("page-history");
    if (!listContainer) {
      listContainer = document.createElement("ul");
      listContainer.id = "page-history";
      listContainer.style.backgroundColor = "#f8f8f8";
      listContainer.style.border = "3px solid #4CAF50";
      listContainer.style.borderRadius = "12px";
      listContainer.style.padding = "10px";
      listContainer.style.marginTop = "10px";
      listContainer.style.listStyle = "none";
      listContainer.style.paddingLeft = "15px";
      logoutLink.parentNode.insertBefore(listContainer, logoutLink.nextSibling);
    } else {
      listContainer.innerHTML = "";
    }

    const collectionItem = document.createElement("li");
    const collectionLink = document.createElement("a");
    collectionLink.href = `https://www.sportscardspro.com/my-collection`;
    collectionLink.textContent = "View Collection";
    collectionLink.style.fontWeight = "bold";
    collectionLink.style.color = "forestgreen";
    collectionItem.appendChild(collectionLink);
    listContainer.appendChild(collectionItem);

    // Populate the list with the last five pages
    pages.forEach((page) => {
      console.log(page);
      const listItem = document.createElement("li");
      const link = document.createElement("a");
      link.href = page;
      const url = new URL(page);
      link.textContent = url.pathname;
      // link.title = url.pathname;
      listItem.appendChild(link);
      listContainer.appendChild(listItem);
    });
  }

  function applyStyles() {
    // Remove "small" class from all <a class="small blue button">
    document.querySelectorAll("a.small.blue.button").forEach((link) => {
      // link.classList.remove('small');
      link.classList.remove("blue");
      link.style.background = "forestgreen";
      link.style.fontSize = "12px";
      link.style.fontWeight = "normal";
    });

    $("head").append(
      "<style>" +
        `
    .button {
  background: forestgreen;
  color: white;
  // padding: 12px 24px;
  // font-size: 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  // box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);    }


    /* Stylish Button */
button {
  background: forestgreen;
  color: white;
  // padding: 12px 24px;
  // font-size: 16px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  // box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}


/* Stylish Select Input */
select {
  // appearance: none;
  background: white;
  border: 2px solid #2196F3;
  padding: 3px 5px !important;
  border-radius: 8px;
  color: #333;
  cursor: pointer;
  transition: border-color 0.3s ease;
}

select:focus {
  border-color: #4CAF50;
  outline: none;
}

#search_type {
   font-size: 14px;
}
.search_button {
  font-size: 14px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.3s ease;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

form.js-search-form {
  height: auto;
}


    ` +
        "</style>"
    );
  }

  // Run the functions
  updatePageHistory();
  displayPageHistory();
  applyStyles();
})();
