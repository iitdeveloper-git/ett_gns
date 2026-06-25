import {expect, test} from "@playwright/test";

test("admin shell exposes primary operations navigation", async ({page}) => {
  await page.goto("/");
  await expect(page.getByText("GNS Console")).toBeVisible();
  await expect(page.getByRole("link", {name: "Applications"})).toBeVisible();
  await expect(page.getByRole("link", {name: "Templates"})).toBeVisible();
  await expect(page.getByRole("link", {name: "Notifications"})).toBeVisible();
});
