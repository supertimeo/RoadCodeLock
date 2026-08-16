async img => {
    const response = await fetch(img.src);
    return Array.from(new Uint8Array(await response.arrayBuffer()));
}