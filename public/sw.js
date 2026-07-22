/*
 * Wyłącznik service workera zostawionego przez poprzednią wersję aplikacji.
 *
 * Ta wersja nie rejestruje żadnego service workera, ale przeglądarki, które
 * odwiedzały starą, wciąż mają go zarejestrowanego i przechwytuje on żądania —
 * stąd nieaktualny wygląd strony w zwykłym oknie przy poprawnym w incognito
 * (tryb prywatny nie uruchamia zarejestrowanych workerów).
 *
 * Sam plik nie da się usunąć zdalnie; przeglądarka musi pobrać nową wersję
 * skryptu, która się wyrejestruje. Dopóki adres zwracał 404, aktualizacja
 * kończyła się niepowodzeniem i stary worker zostawał na miejscu.
 *
 * Brak uchwytu `fetch` jest celowy — ten worker niczego nie przechwytuje.
 *
 * Do usunięcia, gdy w logach przestaną się pojawiać żądania o /sw.js.
 */

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
      await self.registration.unregister();
      // Otwarte karty wciąż trzymają stronę podaną przez starego workera.
      const windows = await self.clients.matchAll({ type: "window" });
      for (const client of windows) client.navigate(client.url);
    })(),
  );
});
