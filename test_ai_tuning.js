const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // Navigate to the app
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    console.log('✓ App loaded');

    // Wait for login or initial page
    await page.waitForTimeout(2000);

    // Try to navigate to AI Tuning page
    // Look for the sidebar or navigation that has AI Tuning option
    const aiTuningButton = await page.$('[data-testid="ai-tuning-nav"]') ||
                           await page.$('button:has-text("AI Tuning")') ||
                           await page.evaluate(() => {
                             const buttons = Array.from(document.querySelectorAll('button'));
                             return buttons.find(b => b.textContent.includes('AI Tuning'));
                           });

    if (aiTuningButton) {
      console.log('✓ Found AI Tuning button, clicking it');
      await aiTuningButton.click();
      await page.waitForTimeout(2000);
    } else {
      console.log('⚠ AI Tuning button not found, checking page content');
    }

    // Take a screenshot
    await page.screenshot({ path: '/home/rahulvadera/cbp-sentry/ai_tuning_page.png', fullPage: true });
    console.log('✓ Screenshot saved to ai_tuning_page.png');

    // Check if tables exist on the page
    const tables = await page.$$('table');
    console.log(`✓ Found ${tables.length} tables on the page`);

    // Check for Model Weights tab content
    const modelWeightsTab = await page.$('text=Model Weights');
    if (modelWeightsTab) {
      console.log('✓ Model Weights tab found');

      // Check if table exists
      const table = await page.$('table');
      if (table) {
        const rows = await page.$$('table tbody tr');
        console.log(`✓ Model Weights table has ${rows.length} rows`);
      } else {
        console.log('⚠ No table found in Model Weights tab');
      }
    }

    // Try to find and click on Screening Rules tab
    const screeningRulesTab = await page.$('button:has-text("Screening Rules")');
    if (screeningRulesTab) {
      console.log('✓ Screening Rules tab found, clicking it');
      await screeningRulesTab.click();
      await page.waitForTimeout(1000);

      const tables2 = await page.$$('table');
      console.log(`✓ Screening Rules tab has ${tables2.length} tables`);
    }

    // Try to find and click on Configuration tab
    const configTab = await page.$('button:has-text("Configuration")');
    if (configTab) {
      console.log('✓ Configuration tab found, clicking it');
      await configTab.click();
      await page.waitForTimeout(1000);

      const tables3 = await page.$$('table');
      console.log(`✓ Configuration tab has ${tables3.length} tables`);
    }

    console.log('✓ Verification complete');
  } catch (error) {
    console.error('✗ Error during verification:', error.message);
  } finally {
    await browser.close();
  }
})();
