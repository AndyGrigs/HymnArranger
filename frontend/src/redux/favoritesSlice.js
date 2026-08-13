import { createSlice } from '@reduxjs/toolkit';

const favoritesSlice = createSlice({
    name: 'favorites',
    initialState: {
        items: [],
    },

    reducers:{
        toggleFavorite: (state, acction) => {
            const camperId = acction.payload;
            const existingIndex = state.items.findIndex(id => id === camperId);

            if (existingIndex>=0) {
                state.items.splice(existingIndex, 1);
            } else {
                state.items.push(camperId)
            }
        }
    }
})

export const {toggleFavorite} = favoritesSlice.actions;

export default favoritesSlice.reducer