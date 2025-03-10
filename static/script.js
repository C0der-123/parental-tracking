// script.js (Client-side Logic)

// Geolocation: Capture and Send User Location
function getLocation() {
  if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(sendLocation, handleError);
  } else {
      alert("Geolocation is not supported by your browser.");
  }
}

// Send Location Data to Server
function sendLocation(position) {
  const data = {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude
  };

  fetch('/update-location', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(result => console.log('Location sent:', result))
  .catch(error => console.error('Error sending location:', error));
}

// Handle Location Errors
function handleError(error) {
  switch (error.code) {
      case error.PERMISSION_DENIED:
          alert("User denied the request for Geolocation.");
          break;
      case error.POSITION_UNAVAILABLE:
          alert("Location information is unavailable.");
          break;
      case error.TIMEOUT:
          alert("The request to get user location timed out.");
          break;
      default:
          alert("An unknown error occurred.");
          break;
  }
}

// Automatically Update Location Every 60 Seconds
setInterval(getLocation, 60000);

// Call getLocation on Page Load
window.onload = getLocation;

// Link Child to Parent
function linkChild(childUsername) {
  fetch('/link-child', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify({ child_username: childUsername })
  })
  .then(response => response.json())
  .then(result => {
      if (result.success) {
          alert('Child linked successfully!');
      } else {
          alert('Error: ' + result.error);
      }
  })
  .catch(error => console.error('Error linking child:', error));
}
