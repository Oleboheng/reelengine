const state = {
  user: null,
  usage: null,
  providers: {
    email: true,
    google: false,
    facebook: false,
  },
};

export function setAuth(data) {
  state.user = data?.user || null;
  state.usage = data?.usage || null;
}

export function clearAuth() {
  state.user = null;
  state.usage = null;
}

export function setProviders(providers) {
  state.providers = {
    ...state.providers,
    ...(providers || {}),
  };
}

export function getState() {
  return state;
}
