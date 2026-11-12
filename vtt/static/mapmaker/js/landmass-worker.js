import {generateLandmass} from './landmass.js';
self.onmessage = ({data}) => {
    try {
        const result = generateLandmass(data.parameters, data.size);
        self.postMessage({id: data.id, ...result}, [result.mask.buffer]);
    } catch (error) { self.postMessage({id: data.id, error: error.message}); }
};
