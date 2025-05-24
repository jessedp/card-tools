document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const imageUploadContainer = document.getElementById("imageUploadContainer");
  const imageFileInput = document.getElementById("imageFile");
  const selectFileButton = document.getElementById("selectFileButton");
  const imagePreview = document.getElementById("imagePreview");
  const searchEbayButton = document.getElementById("searchEbayButton");
  const search130Button = document.getElementById("search130Button");
  const loadingIndicator = document.getElementById("loadingIndicator");
  const errorMessage = document.getElementById("errorMessage");
  const resultsTitle = document.getElementById("resultsTitle");
  const resultsList = document.getElementById("resultsList");
  const ocrResults = document.getElementById("ocrResults");
  const ocrResultLoader = document.getElementById("ocrResultLoader");

  const playerName = document.getElementById("playerName");
  const teamName = document.getElementById("teamName");
  const cardSetYear = document.getElementById("cardSetYear");
  const cardNumber = document.getElementById("cardNumber");
  const serialNumber = document.getElementById("serialNumber");
  const cardType = document.getElementById("cardType");
  const otherText = document.getElementById("otherText");
  const fullText = document.getElementById("fullText");

  // Carousel elements
  const carousel = document.getElementById("carousel");
  const prevButton = document.getElementById("prevButton");
  const nextButton = document.getElementById("nextButton");
  const carouselContainer = document.getElementById("carouselContainer");

  // Data store for image lookups
  const imageLookups = [];
  let currentImageIndex = -1;

  // File input click handler
  selectFileButton.addEventListener("click", () => {
    imageFileInput.click();
  });

  // File input change handler
  imageFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleImageFile(e.target.files[0]);
    }
  });

  // Drag and drop handlers
  imageUploadContainer.addEventListener("dragover", (e) => {
    e.preventDefault();
    imageUploadContainer.classList.add("dragover");
  });

  imageUploadContainer.addEventListener("dragleave", () => {
    imageUploadContainer.classList.remove("dragover");
  });

  imageUploadContainer.addEventListener("drop", (e) => {
    e.preventDefault();
    imageUploadContainer.classList.remove("dragover");

    resetDisplay();

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleImageFile(e.dataTransfer.files[0]);
    }
    if (e.dataTransfer.getData("URL")) {
      handleImageUrl(e.dataTransfer.getData("URL"));
    }
  });

  // Clicking the upload container also triggers file selection
  imageUploadContainer.addEventListener("click", () => {
    imageFileInput.click();
  });

  // Search button handler
  searchEbayButton.addEventListener("click", () => {
    if (selectedFile) {
      searchEbay();
    }
  });

  search130Button.addEventListener("click", () => {
    sendToUserScript("blah", { message: fullText.value })
      .then((response) => console.log("Response:", response))
      .catch((error) => console.error("Error:", error));
  });

  // Carousel navigation
  prevButton.addEventListener("click", () => {
    if (currentImageIndex > 0) {
      currentImageIndex--;
      displayImageLookup(currentImageIndex);
    }
  });

  nextButton.addEventListener("click", () => {
    if (currentImageIndex < imageLookups.length - 1) {
      currentImageIndex++;
      displayImageLookup(currentImageIndex);
    }
  });

  // Handle the selected image file
  async function handleImageFile(file) {
    // Validate file is an image
    if (!file.type.startsWith("image/")) {
      showError("Please select a valid image file.");
      return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      showError("Image file is too large. Please select an image under 5MB.");
      return;
    }

    // Validate image type (jpg/jpeg/png)
    const validTypes = ["image/jpeg", "image/jpg", "image/png"];
    if (!validTypes.includes(file.type)) {
      showError("Please select a JPG or PNG image.");
      return;
    }

    selectedFile = file;

    // Preview the image
    const reader = new FileReader();
    reader.onload = async (e) => {
      const imageDataUrl = e.target.result;
      imagePreview.src = imageDataUrl;
      imagePreview.style.display = "block";
      search130Button.style.display = "block";

      // Hide any previous errors or results
      hideError();
      resultsList.innerHTML = "";
      resultsTitle.style.display = "none";

      // Perform OCR
      const ocrResult = await uploadImageForOCR(file);
      ocrResultLoader.style.display = "none";

      // Store the image lookup
      addImageLookup(imageDataUrl, ocrResult, null); // Initial eBay results are null
    };
    reader.onerror = () => {
      showError("Error reading the file. Please try again.");
    };

    reader.readAsDataURL(file);
  }
  // Handle image file upload
  async function uploadImageForOCR(file) {
    ocrResultLoader.style.display = "block";
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/ocr-image", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("OCR request failed");
      }

      return await response.json();
    } catch (error) {
      console.error("OCR error:", error);
      throw error;
    }
  }
  // Handle the image URL
  async function handleImageUrl(url) {
    // console.log(`ImageURL: ${url}`);
    // Validate URL is an image (basic check)
    // const imageExtensions = [".jpg", ".jpeg", ".png"];
    // const isImageUrl = imageExtensions.some((ext) =>
    //   url.toLowerCase().endsWith(ext)
    // );

    // if (!isImageUrl) {
    //   showError(`Please provide a valid image URL (JPG/JPEG/PNG).  [ ${url} ]`);
    //   return;
    // }
    try {
      // First try to load the image directly
      await loadImageDirectly(url);
    } catch (error) {
      console.log("Direct load failed, trying proxy...", error);
      try {
        // If direct load fails, try through a CORS proxy
        const proxyUrl = `/api/image-proxy?url=${encodeURIComponent(url)}`;
        await loadImageViaProxy(proxyUrl, url);
      } catch (proxyError) {
        showError(
          "Failed to load image. The server may not allow external access.",
        );
        console.error("Proxy load also failed:", proxyError);
      }
    }
  }

  async function loadImageDirectly(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = "Anonymous"; // This is needed for CORS requests

      img.onload = function () {
        processLoadedImage(img, url).then(resolve).catch(reject);
      };

      img.onerror = function () {
        reject(new Error("Failed to load image directly"));
      };

      img.src = url;
    });
  }

  async function loadImageViaProxy(proxyUrl, originalUrl) {
    const img = new Image();

    img.onload = function () {
      processLoadedImage(img, originalUrl);
    };

    img.onerror = function () {
      throw new Error("Failed to load image via proxy");
    };

    img.src = proxyUrl;
  }

  async function loadImageViaPublicProxy(url) {
    // Use a CORS proxy - you can replace with your own proxy server
    const proxyUrl = `https://cors-anywhere.herokuapp.com/${url}`;
    // Alternative proxies you could use:
    // const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`;
    // const proxyUrl = `https://thingproxy.freeboard.io/fetch/${url}`;

    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = "Anonymous";

      img.onload = function () {
        processLoadedImage(img, url).then(resolve).catch(reject);
      };

      img.onerror = function () {
        reject(new Error("Failed to load image via proxy"));
      };

      img.src = proxyUrl;
    });
  }

  async function processLoadedImage(img, originalUrl) {
    // Check image dimensions if needed (optional)
    // if (img.width > 5000 || img.height > 5000) {
    //   throw new Error("Image dimensions are too large.");
    // }

    // Convert the loaded image to a data URL
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);

    // Check file size by converting to data URL
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    if (dataUrl.length > (5 * 1024 * 1024) / 1.33) {
      throw new Error("Image is too large. Please select an image under 5MB.");
    }

    // Set the preview image
    imagePreview.src = dataUrl;
    imagePreview.style.display = "block";
    searchEbayButton.style.display = "block";

    // Create a synthetic file object
    selectedFile = dataUrlToFile(dataUrl, getFilenameFromUrl(originalUrl));

    // Hide any previous errors or results
    hideError();
    resultsList.innerHTML = "";
    resultsTitle.style.display = "none";
  }

  function getFilenameFromUrl(url) {
    try {
      const urlObj = new URL(url);
      const pathname = urlObj.pathname;
      return pathname.split("/").pop() || "image.jpg";
    } catch {
      return "image.jpg";
    }
  }

  // Helper function to convert data URL to File object
  function dataUrlToFile(dataUrl, filename) {
    const arr = dataUrl.split(",");
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);

    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }

    return new File([u8arr], filename, { type: mime });
  }

  // Display OCR results in auto-selecting fields
  function displayOCRResults(data) {
    const fields = [
      { id: "playerName", value: data.player_name },
      { id: "teamName", value: data.team_name },
      { id: "cardSetYear", value: data.card_set_year },
      { id: "cardNumber", value: data.card_number },
      { id: "serialNumber", value: data.serial_number },
      { id: "cardType", value: data.card_type },
      { id: "otherText", value: data.other },
    ];

    fields.forEach((field) => {
      const element = document.getElementById(field.id);
      if (element) {
        element.value = field.value || "";

        // Add auto-select behavior
        element.addEventListener("focus", function () {
          this.select();
          document.execCommand("copy");

          // Optional: Show a "copied" tooltip
          const tooltip = document.createElement("span");
          tooltip.className = "copy-tooltip";
          tooltip.textContent = "Copied!";
          this.parentNode.appendChild(tooltip);

          setTimeout(() => {
            tooltip.remove();
          }, 2000);
        });
      }
    });
    const serial = serialNumber.value.includes("/")
      ? "/" + serialNumber.value.split("/")[1]
      : serialNumber.value;
    const full = `${cardSetYear.value} ${playerName.value} ${cardNumber.value} ${cardType.value} ${serial} ${otherText.value}`;
    fullText.value = full;

    // Show the results section
    ocrResults.style.display = "block";
    searchEbayButton.style.display = "block";
  }

  // Search eBay with the selected image
  async function searchEbay() {
    if (!selectedFile) {
      showError("Please select an image first.");
      return;
    }

    try {
      // Show loading indicator
      loadingIndicator.style.display = "block";
      searchEbayButton.disabled = true;
      hideError();
      resultsList.innerHTML = "";
      resultsTitle.style.display = "none";

      // Create FormData to send the file
      const formData = new FormData();
      formData.append("imageFile", selectedFile);

      // Send to our backend API
      const response = await fetch("/api/search-ebay", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        let errorMessage = "Failed to search eBay";

        if (errorData.details && errorData.details.errors) {
          errorMessage = errorData.details.errors
            .map(
              (err) =>
                `${err.message}${err.longMessage ? `: ${err.longMessage}` : ""}`,
            )
            .join(". ");
        } else if (errorData.error) {
          errorMessage = errorData.error;
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();
      // Store the eBay results in the current image lookup
      if (currentImageIndex >= 0 && currentImageIndex < imageLookups.length) {
        imageLookups[currentImageIndex].ebayResults = data;
      }
      displayResults(data);
    } catch (error) {
      showError(error.message || "An error occurred during the search.");
    } finally {
      // Hide loading indicator
      loadingIndicator.style.display = "none";
      searchEbayButton.disabled = false;
    }
  }

  // Display eBay search results
  function displayResults(data) {
    resultsList.innerHTML = "";

    if (!data.itemSummaries || data.itemSummaries.length === 0) {
      resultsList.innerHTML =
        '<p class="no-results">No results found. Try a different image.</p>';
      resultsTitle.style.display = "block";
      return;
    }

    resultsTitle.style.display = "block";

    data.itemSummaries.forEach((item) => {
      // console.log(">>>", item);
      const resultItem = document.createElement("div");
      resultItem.className = "result-item";

      // Image
      let imageHtml = "";
      if (item.image && item.image.imageUrl) {
        imageHtml = `<img src="${item.image.imageUrl}" alt="${item.title}" class="result-image">`;
      } else {
        imageHtml = '<div class="result-image no-image">No Image</div>';
      }

      // Title
      const title = item.title || "No Title";

      const searchLinkHtml = `[<a target="_blank" href="https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(
        title,
      )}&_sacat=0&_sop=12&LH_Sold=1&LH_Complete=1&rt=nc&LH_All=1">search sold</a>]`;

      // Price
      let priceHtml = "";
      if (item.price) {
        priceHtml = `<div class="result-price">${item.price.currency} ${item.price.value}</div>`;
      } else {
        priceHtml = '<div class="result-price">Price not available</div>';
      }

      // Link to eBay
      let linkHtml = "";
      if (item.itemWebUrl) {
        linkHtml = `<a href="${item.itemWebUrl}" target="_blank" class="result-link">View on eBay</a>`;
      }

      resultItem.innerHTML = `
                ${imageHtml}
                <div class="result-title">${title}</div>
                <div>${searchLinkHtml}</div>
                ${priceHtml}
                ${linkHtml}
            `;

      resultsList.appendChild(resultItem);
    });
  }

  // Show error message
  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = "block";
  }

  // Hide error message
  function hideError() {
    errorMessage.textContent = "";
    errorMessage.style.display = "none";
  }

  // --- Carousel Functions ---
  function addImageLookup(imageDataUrl, ocrResult, ebayResults) {
    imageLookups.push({
      imageDataUrl: imageDataUrl,
      ocrResult: ocrResult,
      ebayResults: ebayResults,
    });
    currentImageIndex = imageLookups.length - 1; // Update current index

    updateCarousel();
    displayImageLookup(currentImageIndex);
  }

  function updateCarousel() {
    // Clear the carousel
    carousel.innerHTML = "";

    // Add images to the carousel
    imageLookups.forEach((lookup, index) => {
      const img = document.createElement("img");
      img.src = lookup.imageDataUrl;
      img.alt = `Image ${index + 1}`;
      img.addEventListener("click", () => displayImageLookup(index));
      carousel.appendChild(img);
    });

    // Show carousel and navigation buttons if there are images
    if (imageLookups.length > 0) {
      carouselContainer.style.display = "flex"; // Or whatever display style you prefer
      prevButton.style.display = "block";
      nextButton.style.display = "block";
    } else {
      carouselContainer.style.display = "none";
      prevButton.style.display = "none";
      nextButton.style.display = "none";
    }

    // Enable/disable navigation buttons based on current index
    prevButton.disabled = currentImageIndex <= 0;
    nextButton.disabled = currentImageIndex >= imageLookups.length - 1;
  }

  function displayImageLookup(index) {
    const lookup = imageLookups[index];
    imagePreview.src = lookup.imageDataUrl;
    imagePreview.style.display = "block";
    displayOCRResults(lookup.ocrResult);
    if (lookup.ebayResults) {
      displayResults(lookup.ebayResults); // Display stored eBay results
    } else {
      // Clear existing results if no eBay results are stored
      resultsList.innerHTML = "";
      resultsTitle.style.display = "none";
    }

    currentImageIndex = index;
    updateCarousel(); // Update carousel to reflect current selection
  }

  function resetDisplay() {
    imagePreview.style.display = "none";
    searchEbayButton.style.display = "none";
    search130Button.style.display = "none";
    ocrResults.style.display = "none";
    ocrResultLoader.style.display = "none";
    hideError();
    resultsList.innerHTML = "";
    resultsTitle.style.display = "none";
  }
});

// Simple client to send data to the UserScript via the server
async function sendToUserScript(clientId, data) {
  try {
    const response = await fetch("https://local.lastseen.me:8050/ps/publish", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        client_id: clientId,
        data: data,
      }),
    });

    return await response.json();
  } catch (error) {
    console.error("Error sending data:", error);
    throw error;
  }
}

// Example usage:
// sendToUserScript('client-id-from-userscript', { message: 'Hello from website!' })
//   .then(response => console.log('Response:', response))
//   .catch(error => console.error('Error:', error));
