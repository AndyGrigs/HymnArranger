import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { fetchCampers, fetchCamperById } from "../services/api";


export const fetchCampersByPage = createAsyncThunk(
  "campers/fetchCampersByPage",
  async ({ page, filters }, { rejectWithValue }) => {
    try {
      const data = await fetchCampers(page, filters);
      return data.items || data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);
export const fetchCamperDetails = createAsyncThunk(
  "campers/fetchCamperDetails",
  async (id, { rejectWithValue }) => {
    try {
      const data = await fetchCamperById(id);
      return data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

const campersSlice = createSlice({
  name: "campers",
  initialState: {
    list: [],
    currentCamper: null,
    page: 1,
    filters: {
      location: "",
      type: "",
      form: "",
      AC: false,
      automatic: false,
      kitchen: false,
      TV: false,
      bathroom: false,
    },
    loading: false,
    error: null,
    hasMore: true,
  },
  reducers: {
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
      state.page = 1;
      state.hasMore = true;
      state.list = [];
    },

    clearFilters: (state) => {
      state.filters = {
        location: "",
        type: "",
        form: "",
        AC: false,
        automatic: false,
        kitchen: false,
        TV: false,
        bathroom: false,
      };
      state.page = 1;
      state.list = [];
      state.hasMore = true;
    },
    resetPage: (state) => {
      state.page = 1;
      state.hasMore = true;
      state.list = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCampersByPage.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCampersByPage.fulfilled, (state, action) => {
        state.loading = false;
        const newCampers = action.payload;
        if (state.page === 1) {
          state.list = newCampers;
        } else {
          state.list.push(...newCampers);
        }
        state.page += 1;
        state.hasMore = newCampers.length === 4;
      })

      .addCase(fetchCampersByPage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      .addCase(fetchCamperDetails.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCamperDetails.fulfilled, (state, action) => {
        state.loading = false;
        state.currentCamper = action.payload;
      })
      .addCase(fetchCamperDetails.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { setFilters, clearFilters, resetPage} = campersSlice.actions;
export default campersSlice.reducer;
