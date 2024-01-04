


/** @type {import('@sveltejs/kit').Handle} */
export async function handle({event, resolve }) {
    const cookie = event.cookies.get("jwt");
    if(!cookie) {
        event.locals.isAuth = false;
    }else{
        event.locals.isAuth = true;
        event.locals.jwt = cookie;
    }
    return resolve(event);
}