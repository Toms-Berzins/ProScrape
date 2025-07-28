import { error } from '@sveltejs/kit';
import { ListingsApi } from '$lib/api/listings';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url, fetch }) => {
	try {
		// Load the main listing
		const listingResponse = await ListingsApi.getListing(params.id, fetch);
		
		if (listingResponse.error || !listingResponse.data) {
			throw error(404, {
				message: 'Listing not found',
				details: listingResponse.error || 'The requested listing could not be found'
			});
		}

		const listing = listingResponse.data;

		// Load similar listings in parallel
		const similarListingsPromise = ListingsApi.getSimilarListings(params.id, 4, fetch);

		try {
			const [similarListingsResponse] = await Promise.all([
				similarListingsPromise
			]);

			return {
				listing,
				similarListings: similarListingsResponse.data || [],
				meta: {
					title: listing.title,
					description: listing.description || `${listing.title} - ${listing.price} - ${listing.area_sqm ? listing.area_sqm + 'm²' : ''} property for sale`,
					image: listing.image_urls?.[0],
					url: url.toString()
				}
			};
		} catch (err) {
			// If similar listings fail, still return the main listing
			console.warn('Failed to load similar listings:', err);
			
			return {
				listing,
				similarListings: [],
				meta: {
					title: listing.title,
					description: listing.description || `${listing.title} - ${listing.price} - ${listing.area_sqm ? listing.area_sqm + 'm²' : ''} property for sale`,
					image: listing.image_urls?.[0],
					url: url.toString()
				}
			};
		}
	} catch (err) {
		console.error('Error loading listing:', err);
		
		if (err.status === 404) {
			throw err;
		}
		
		throw error(500, {
			message: 'Failed to load listing',
			details: 'An error occurred while loading the listing details'
		});
	}
};

export const prerender = false;