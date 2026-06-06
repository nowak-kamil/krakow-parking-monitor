/**
 * A Google Apps Script designed to automatically initiate a GitHub Actions:
 * 1. Sends a POST request to the GitHub API to trigger a specific process.
 * 2. Manages internal time-based triggers within Google Apps Script.
 * 3. Pre-configured to execute every 30 minutes (on the hour and half-hour).
 * * USAGE INSTRUCTIONS:
 * 1. Replace the GITHUB_TOKEN constant with your personal GitHub token.
 * 2. Run the 'setupTrigger()' function ONCE manually to initialize the schedule.
 * 3. Use 'removeTrigger()' to clear all active schedules.
 * 4. Use 'listTriggers()' to verify the current status in the execution logs.
 */

const GITHUB_TOKEN = '[ENTER TOKEN]'
const REPO_OWNER = 'nowak-kamil';
const REPO_NAME  = 'krakow-parking-monitor';
const EVENT_TYPE   = "pipedream_trigger";

const TRIGGER_URL  = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/dispatches`;

// MAIN: called by the time-based trigger

function triggerGitHubActions() {
  const now = new Date();
  const hour    = now.getHours();
  const minutes = now.getMinutes();

  Logger.log(`[${now.toISOString()}] Trigger fired — current time: ${hour}:${String(minutes).padStart(2, "0")}`);

  try {
    const payload = {
      event_type: EVENT_TYPE,
      client_payload: {
        triggered_at: now.toISOString(),
        source: "google_apps_script"
      }
    };

    const options = {
      method: "post",
      contentType: "application/json",
      headers: {
        "Authorization": `Bearer ${GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(TRIGGER_URL, options);
    const statusCode = response.getResponseCode();

    if (statusCode === 204) {
      Logger.log("GitHub Actions workflow triggered successfully.");
    } else {
      Logger.log(`Unexpected response: HTTP ${statusCode}`);
      Logger.log(`   Body: ${response.getContentText()}`);
    }

  } catch (error) {
    Logger.log(`Error triggering workflow: ${error.message}`);
  }
}


// SETUP: creates a time-based trigger running every 30 minutes
// Run this function ONCE manually from the Apps Script editor

function setupTrigger() {
  removeTrigger();

  // Fires at :00 of every hour
  ScriptApp.newTrigger("triggerGitHubActions")
    .timeBased()
    .everyHours(1)
    .nearMinute(0)
    .create();

  // Fires at :30 of every hour
  ScriptApp.newTrigger("triggerGitHubActions")
    .timeBased()
    .everyHours(1)
    .nearMinute(30)
    .create();

  Logger.log("Two triggers created: at :00 and :30 of every hour.");
}

// CLEANUP: removes all triggers for triggerGitHubActions

function removeTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  let removed = 0;

  for (const trigger of triggers) {
    if (trigger.getHandlerFunction() === "triggerGitHubActions") {
      ScriptApp.deleteTrigger(trigger);
      removed++;
    }
  }

  if (removed > 0) {
    Logger.log(`Removed ${removed} existing trigger(s).`);
  }
}

// UTILITY: lists all active triggers (for debugging)

function listTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  if (triggers.length === 0) {
    Logger.log("No active triggers found.");
    return;
  }
  triggers.forEach((t, i) => {
    Logger.log(`[${i + 1}] Function: ${t.getHandlerFunction()} | Type: ${t.getEventType()}`);
  });
}


