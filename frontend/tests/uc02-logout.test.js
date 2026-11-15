import assert from "node:assert/strict";
import { test } from "node:test";
import { clearSession, sessionGate } from "../src/features/auth/session.js";
import { TOKEN_KEY } from "../src/lib/api/client.js";

function sessionFixture(token = "valid-token") {
  const values = new Map([["unrelated", "keep-me"]]);
  if (token) values.set(TOKEN_KEY, token);
  const calls = [];
  const storage = {
    getItem: (key) => values.get(key) ?? null,
    removeItem: (key) => {
      calls.push(["removeItem", key]);
      values.delete(key);
    },
  };
  const queryClient = {
    cancelQueries: () => calls.push(["cancelQueries"]),
    removeQueries: () => calls.push(["removeQueries"]),
  };
  return { storage, queryClient, calls };
}

// UC-02 AC-1: Đăng xuất kết thúc phiên
test("logout removes the token, cancels queries and clears their cache in order", () => {
  const { storage, queryClient, calls } = sessionFixture();

  clearSession({ storage, queryClient });

  assert.equal(storage.getItem(TOKEN_KEY), null);
  assert.equal(storage.getItem("unrelated"), "keep-me");
  assert.deepEqual(calls, [
    ["removeItem", TOKEN_KEY],
    ["cancelQueries"],
    ["removeQueries"],
  ]);
});

// UC-02 AC-2: Phải đăng nhập lại sau khi đăng xuất
test("opening a protected page after logout requires login even with a stale user", () => {
  const { storage, queryClient } = sessionFixture();

  clearSession({ storage, queryClient });

  assert.equal(
    sessionGate({
      token: storage.getItem(TOKEN_KEY),
      user: { id: 17 },
      isPending: false,
      isError: false,
    }),
    "login",
  );
});

for (const user of [null, { id: 17 }]) {
  for (const isPending of [false, true]) {
    for (const isError of [false, true]) {
      // UC-02 A1: Mở lại trang cần đăng nhập sau khi đăng xuất
      test(`no token requires login: user=${Boolean(user)}, pending=${isPending}, error=${isError}`, () => {
        assert.equal(sessionGate({ token: null, user, isPending, isError }), "login");
      });
    }
  }
}

// UC-02 A2: Phiên đã kết thúc từ trước
test("logout without a stored token still clears queries and can be repeated", () => {
  const { storage, queryClient, calls } = sessionFixture(null);

  assert.doesNotThrow(() => clearSession({ storage, queryClient }));
  assert.doesNotThrow(() => clearSession({ storage, queryClient }));

  assert.equal(storage.getItem(TOKEN_KEY), null);
  assert.deepEqual(calls, [
    ["removeItem", TOKEN_KEY],
    ["cancelQueries"],
    ["removeQueries"],
    ["removeItem", TOKEN_KEY],
    ["cancelQueries"],
    ["removeQueries"],
  ]);
});

// UC-02 A2: Phiên đã kết thúc từ trước
test("a token without a verified user requires login when verification ends", () => {
  assert.equal(
    sessionGate({ token: "old-token", user: null, isPending: false, isError: false }),
    "login",
  );
});

for (const user of [null, { id: 17 }]) {
  // UC-02 A2: Phiên đã kết thúc từ trước — lỗi xác minh phiên
  test(`verification error keeps the error screen with user=${Boolean(user)}`, () => {
    assert.equal(
      sessionGate({ token: "old-token", user, isPending: false, isError: true }),
      "error",
    );
  });
}

for (const isPending of [false, true]) {
  // UC-02 AC-1: Đăng xuất kết thúc phiên — đối chứng phiên hợp lệ
  test(`a token and user allow access with pending=${isPending}`, () => {
    assert.equal(
      sessionGate({ token: "valid-token", user: { id: 17 }, isPending, isError: false }),
      "allow",
    );
  });
}

for (const isError of [false, true]) {
  // UC-02 A2: Phiên đã kết thúc từ trước — chờ xác minh trước khi xử lý lỗi
  test(`verification without a user keeps the checking screen with error=${isError}`, () => {
    assert.equal(
      sessionGate({ token: "valid-token", user: null, isPending: true, isError }),
      "checking",
    );
  });
}
