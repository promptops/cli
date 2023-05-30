exports.handler = async (event, context) => {
    // Return the JSON response
    return {
        statusCode: 200,
        body: JSON.stringify({message: 'hello-world'}),
        headers: {
            'Content-Type': 'application/json',
        },
    };
};
