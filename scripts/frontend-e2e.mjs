import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseURL = process.env.FRONTEND_BASE_URL || "http://127.0.0.1:8000";

async function selectRoomUser(page, suffix) {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await page
    .locator("label.profile-option", { hasText: "Usuário da Sala" })
    .click();
  await page.locator('input[name="user_reference"]').fill(`e2e-user-${suffix}`);
  await page.locator('select[name="affiliation_type"]').selectOption("STUDENT");
  await page
    .locator('input[name="institutional_unit"]')
    .fill("Sistemas de Informação");
  await page.getByRole("button", { name: "Entrar no ambiente" }).click();
  await page.waitForURL("**/sala/computadores/");
}

async function selectProfile(page, profileName, destination) {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await page
    .locator("label.profile-option", { hasText: profileName })
    .click();
  await page.getByRole("button", { name: "Entrar no ambiente" }).click();
  await page.waitForURL(destination);
}

async function swipe(locator, { fromX, toX, fromY = 300, toY = 305 }) {
  await locator.dispatchEvent("pointerdown", {
    pointerType: "touch",
    pointerId: 1,
    clientX: fromX,
    clientY: fromY,
  });
  await locator.dispatchEvent("pointerup", {
    pointerType: "touch",
    pointerId: 1,
    clientX: toX,
    clientY: toY,
  });
}

const browser = await chromium.launch({ headless: true });
const pageErrors = [];

try {
  const mobile = await browser.newContext({
    viewport: { width: 420, height: 900 },
    hasTouch: true,
    isMobile: true,
  });
  const mobilePage = await mobile.newPage();
  mobilePage.on("pageerror", (error) => pageErrors.push(error.message));
  await selectRoomUser(mobilePage, "mobile");

  assert.equal(
    await mobilePage.locator(".app-header").evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    ),
    "rgb(12, 76, 164)",
  );
  await swipe(mobilePage.locator(".computer-list"), { fromX: 360, toX: 70 });
  await mobilePage.waitForURL("**day=tomorrow**");
  await mobilePage.waitForSelector('[data-day="tomorrow"][aria-current="page"]');

  const tomorrowURL = mobilePage.url();
  await swipe(mobilePage.locator(".computer-list"), { fromX: 360, toX: 70 });
  await mobilePage.waitForTimeout(180);
  assert.equal(mobilePage.url(), tomorrowURL, "Amanhã é o limite final dos dias");

  await swipe(mobilePage.locator(".computer-list"), { fromX: 70, toX: 360 });
  await mobilePage.waitForURL("**day=today**");
  const todayURL = mobilePage.url();
  await swipe(mobilePage.locator(".computer-list"), { fromX: 220, toX: 260 });
  await mobilePage.waitForTimeout(180);
  assert.equal(mobilePage.url(), todayURL, "Gestos menores que 56 px são ignorados");

  await swipe(mobilePage.locator(".mobile-navigation"), {
    fromX: 70,
    toX: 360,
    fromY: 850,
    toY: 850,
  });
  await mobilePage.waitForTimeout(180);
  assert.equal(mobilePage.url(), todayURL, "Computadores é o limite inicial");

  await swipe(mobilePage.locator(".mobile-navigation"), {
    fromX: 360,
    toX: 70,
    fromY: 850,
    toY: 850,
  });
  await mobilePage.waitForURL("**/sala/agenda/");
  assert.ok(await mobilePage.locator('[data-nav-key="agenda"][aria-current="page"]').count());

  const agendaURL = mobilePage.url();
  await swipe(mobilePage.locator(".mobile-navigation"), {
    fromX: 220,
    toX: 230,
    fromY: 850,
    toY: 730,
  });
  await mobilePage.waitForTimeout(180);
  assert.equal(mobilePage.url(), agendaURL, "Rolagem vertical não deve trocar a tela");

  await swipe(mobilePage.locator(".mobile-navigation"), {
    fromX: 70,
    toX: 360,
    fromY: 850,
    toY: 850,
  });
  await mobilePage.waitForURL("**/sala/computadores/");

  await mobilePage.locator('[data-nav-key="problems"]').last().click();
  await mobilePage.waitForURL("**/sala/problemas/");
  const problemsURL = mobilePage.url();
  await swipe(mobilePage.locator(".mobile-navigation"), {
    fromX: 360,
    toX: 70,
    fromY: 850,
    toY: 850,
  });
  await mobilePage.waitForTimeout(180);
  assert.equal(mobilePage.url(), problemsURL, "Problemas é o limite final");
  await mobile.close();

  const monitorMobile = await browser.newContext({
    viewport: { width: 420, height: 900 },
    hasTouch: true,
    isMobile: true,
  });
  const monitorPage = await monitorMobile.newPage();
  monitorPage.on("pageerror", (error) => pageErrors.push(error.message));
  await selectProfile(monitorPage, "Monitor da Sala", "**/monitor/");
  assert.equal(await monitorPage.locator(".staff-sidebar").isVisible(), false);
  assert.equal(
    await monitorPage.locator(".staff-mobile-navigation").isVisible(),
    true,
  );
  assert.equal(
    await monitorPage.locator(".staff-header").evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    ),
    "rgb(12, 76, 164)",
  );
  await monitorPage.getByRole("link", { name: "Ocorrências" }).last().click();
  await monitorPage.waitForURL("**/monitor/ocorrencias/");
  await monitorPage.getByText("Registrar nova ocorrência", { exact: true }).click();
  await monitorPage.locator('select[name="computer_id"]').selectOption({ index: 1 });
  await monitorPage
    .locator('textarea[name="description"]')
    .fill("Ocorrência criada pelo fluxo E2E do Monitor.");
  await monitorPage
    .getByRole("button", { name: "Registrar ocorrência" })
    .click();
  await monitorPage.waitForURL("**/monitor/ocorrencias/");
  assert.equal(
    await monitorPage.getByText("Ocorrência atualizada.").count(),
    0,
  );
  assert.ok(
    await monitorPage
      .getByText("Ocorrência criada pelo fluxo E2E do Monitor.")
      .count(),
  );
  await monitorMobile.close();

  const desktop = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const desktopPage = await desktop.newPage();
  desktopPage.on("pageerror", (error) => pageErrors.push(error.message));
  await selectRoomUser(desktopPage, "desktop");
  assert.equal(await desktopPage.locator(".desktop-sidebar").isVisible(), true);
  assert.equal(await desktopPage.locator(".mobile-navigation").isVisible(), false);
  assert.equal(await desktopPage.getByRole("heading", { name: "Sala de Informática" }).first().isVisible(), true);
  await desktop.close();

  const supervisorDesktop = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const supervisorPage = await supervisorDesktop.newPage();
  supervisorPage.on("pageerror", (error) => pageErrors.push(error.message));
  await selectProfile(
    supervisorPage,
    "Supervisor da Biblioteca",
    "**/supervisor/",
  );
  assert.equal(await supervisorPage.locator(".staff-sidebar").isVisible(), true);
  assert.equal(
    await supervisorPage.locator(".staff-mobile-navigation").isVisible(),
    false,
  );
  await supervisorPage
    .getByRole("link", { name: "Inventário", exact: true })
    .click();
  await supervisorPage.waitForURL("**/supervisor/computadores/");
  assert.ok(
    await supervisorPage.getByRole("heading", {
      name: "Inventário de computadores",
    }).count(),
  );
  await supervisorPage
    .getByRole("link", { name: "Funcionamento", exact: true })
    .click();
  await supervisorPage.waitForURL("**/supervisor/funcionamento/");
  await supervisorPage.getByRole("link", { name: "Parâmetros" }).click();
  await supervisorPage.waitForURL("**section=policies");
  assert.ok(
    await supervisorPage.getByRole("heading", { name: "Política vigente" }).count(),
  );
  await supervisorPage
    .getByRole("link", { name: "Relatórios", exact: true })
    .click();
  await supervisorPage.waitForURL("**/supervisor/relatorios/");
  assert.ok(
    await supervisorPage.getByRole("heading", { name: "Relatório mensal" }).count(),
  );
  await supervisorDesktop.close();

  const noScript = await browser.newContext({
    viewport: { width: 420, height: 900 },
    javaScriptEnabled: false,
  });
  const noScriptPage = await noScript.newPage();
  await selectRoomUser(noScriptPage, "sem-javascript");
  assert.equal(
    await noScriptPage.getByRole("link", { name: "Agenda" }).last().isVisible(),
    true,
  );
  await selectProfile(noScriptPage, "Monitor da Sala", "**/monitor/");
  await noScriptPage
    .getByRole("link", { name: "Computadores", exact: true })
    .last()
    .click();
  await noScriptPage.waitForURL("**/monitor/computadores/");
  assert.equal(
    await noScriptPage.getByText("Alterar estado", { exact: true }).first().isVisible(),
    true,
  );
  await noScript.close();

  assert.deepEqual(pageErrors, [], `Erros JavaScript: ${pageErrors.join("; ")}`);
} finally {
  await browser.close();
}
